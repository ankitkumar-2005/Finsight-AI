import csv
from datetime import date, timedelta
from io import StringIO

from flask import Blueprint, Response, jsonify, request, session

from .calculations import savings_percentage
from .database import connection


reports_bp = Blueprint("reports", __name__)
RANGES = {"last_7_days", "last_30_days", "this_month", "last_month", "custom"}


def _month_start(value):
    return date(value.year, value.month, 1)


def _next_month(value):
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def report_period(args):
    selected = args.get("range", "this_month")
    if selected not in RANGES:
        return None, None, {"error": "Choose a supported analytics date range."}
    today = date.today()
    if selected == "last_7_days":
        start = today - timedelta(days=6)
        end = today
    elif selected == "last_30_days":
        start = today - timedelta(days=29)
        end = today
    elif selected == "this_month":
        start = _month_start(today)
        end = today
    elif selected == "last_month":
        end = _month_start(today) - timedelta(days=1)
        start = _month_start(end)
    else:
        try:
            start = date.fromisoformat(args.get("date_from", ""))
            end = date.fromisoformat(args.get("date_to", ""))
        except ValueError:
            return None, None, {"error": "Enter valid start and end dates for the custom range."}
        if start > end:
            return None, None, {"error": "Start date must be on or before end date."}
        if (end - start).days > 365:
            return None, None, {"error": "Custom analytics ranges can be at most 366 days."}
    return start, end, None


def _user_id():
    return session.get("user_id")


def _text_cell(value):
    text = str(value or "")
    return f"'{text}" if text[:1] in {"=", "+", "-", "@", "\t", "\r"} else text


def _query_records(user_id, start, end):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT transaction_date, title, type, category, amount, payment_method, description
               FROM transactions WHERE user_id = %s AND transaction_date >= %s AND transaction_date < %s
               ORDER BY transaction_date, id""",
            (user_id, start, end + timedelta(days=1)),
        )
        rows = cursor.fetchall()
        cursor.close()
    return rows


@reports_bp.get("")
def analytics_report():
    user_id = _user_id()
    if not user_id:
        return jsonify({"error": "Authentication is required."}), 401
    start, end, error = report_period(request.args)
    if error:
        return jsonify(error), 400
    end_exclusive = end + timedelta(days=1)
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0),
                COUNT(*)
               FROM transactions WHERE user_id = %s AND transaction_date >= %s AND transaction_date < %s""",
            (user_id, start, end_exclusive),
        )
        income_total, expense_total, transaction_count = cursor.fetchone()
        cursor.execute(
            """SELECT DATE_FORMAT(transaction_date, '%%Y-%%m') AS month,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0)
               FROM transactions WHERE user_id = %s AND transaction_date >= %s AND transaction_date < %s
               GROUP BY DATE_FORMAT(transaction_date, '%%Y-%%m') ORDER BY month""",
            (user_id, start, end_exclusive),
        )
        grouped_months = {row[0]: (float(row[1]), float(row[2])) for row in cursor.fetchall()}
        cursor.execute(
            """SELECT category, SUM(amount) FROM transactions
               WHERE user_id = %s AND type = 'expense' AND transaction_date >= %s AND transaction_date < %s
               GROUP BY category ORDER BY SUM(amount) DESC, category""",
            (user_id, start, end_exclusive),
        )
        categories = [{"category": row[0], "amount": float(row[1])} for row in cursor.fetchall()]
        cursor.execute(
            """SELECT DATE_FORMAT(transaction_date, '%%Y-%%m-%%d') AS day,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0)
               FROM transactions WHERE user_id = %s AND transaction_date >= %s AND transaction_date < %s
               GROUP BY DATE_FORMAT(transaction_date, '%%Y-%%m-%%d') ORDER BY day""",
            (user_id, start, end_exclusive),
        )
        grouped_days = {row[0]: (float(row[1]), float(row[2])) for row in cursor.fetchall()}
        cursor.execute("SELECT currency FROM financial_profiles WHERE user_id = %s", (user_id,))
        currency_row = cursor.fetchone()
        cursor.close()

    monthly_reports = []
    month = _month_start(start)
    final_month = _month_start(end)
    while month <= final_month:
        key = month.strftime("%Y-%m")
        month_income, month_expenses = grouped_months.get(key, (0.0, 0.0))
        net = month_income - month_expenses
        monthly_reports.append({"month": key, "income": month_income, "expenses": month_expenses, "savings": net, "savings_percentage": savings_percentage(month_income, month_expenses)})
        month = _next_month(month)

    trend = []
    current = start
    while current <= end:
        income, expenses = grouped_days.get(current.isoformat(), (0.0, 0.0))
        trend.append({"date": current.isoformat(), "income": income, "expenses": expenses, "savings": income - expenses})
        current += timedelta(days=1)

    income_total = float(income_total)
    expense_total = float(expense_total)
    return jsonify({
        "range": request.args.get("range", "this_month"),
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "currency": currency_row[0] if currency_row else "INR",
        "summary": {"income": income_total, "expenses": expense_total, "savings": income_total - expense_total, "savings_percentage": savings_percentage(income_total, expense_total), "transaction_count": transaction_count},
        "monthly_reports": monthly_reports,
        "category_expenses": categories,
        "highest_spending_categories": categories[:5],
        "trend": trend,
    })


@reports_bp.get("/export")
def export_report():
    user_id = _user_id()
    if not user_id:
        return jsonify({"error": "Authentication is required."}), 401
    start, end, error = report_period(request.args)
    if error:
        return jsonify(error), 400
    records = _query_records(user_id, start, end)
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Date", "Title", "Type", "Category", "Amount", "Currency", "Payment method", "Description"])
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT currency FROM financial_profiles WHERE user_id = %s", (user_id,))
        currency_row = cursor.fetchone()
        cursor.close()
    currency = currency_row[0] if currency_row else "INR"
    for transaction_date, title, transaction_type, category, amount, payment_method, description in records:
        writer.writerow([transaction_date.isoformat(), _text_cell(title), transaction_type, _text_cell(category), f"{amount:.2f}", currency, payment_method, _text_cell(description)])
    filename = f"finsight-report-{start.isoformat()}-to-{end.isoformat()}.csv"
    return Response(output.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})
