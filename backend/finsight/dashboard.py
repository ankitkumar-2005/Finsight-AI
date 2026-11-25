from datetime import date, timedelta

from flask import Blueprint, jsonify, session

from .database import connection
from .transactions import _serialize


dashboard_bp = Blueprint("dashboard", __name__)


def _month_start(offset=0):
    today = date.today()
    month_index = today.year * 12 + (today.month - 1) - offset
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)


@dashboard_bp.get("/summary")
def summary():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication is required."}), 401
    this_month = _month_start()
    next_month = _month_start(-1)
    first_month = _month_start(11)
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0)
               FROM transactions WHERE user_id = %s""", (user_id,)
        )
        total_income, total_expenses = cursor.fetchone()
        cursor.execute(
            """SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0)
               FROM transactions WHERE user_id = %s AND transaction_date >= %s AND transaction_date < %s""",
            (user_id, this_month, next_month),
        )
        monthly_income, monthly_expenses = cursor.fetchone()
        cursor.execute(
            """SELECT DATE_FORMAT(transaction_date, '%%Y-%%m') AS month,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0)
               FROM transactions WHERE user_id = %s AND transaction_date >= %s AND transaction_date < %s
               GROUP BY DATE_FORMAT(transaction_date, '%%Y-%%m') ORDER BY month""",
            (user_id, first_month, next_month),
        )
        grouped_months = {row[0]: (float(row[1]), float(row[2])) for row in cursor.fetchall()}
        months = []
        for offset in range(11, -1, -1):
            month_date = _month_start(offset)
            income, expenses = grouped_months.get(month_date.strftime("%Y-%m"), (0.0, 0.0))
            months.append({"month": month_date.strftime("%Y-%m"), "income": income, "expenses": expenses, "savings": income - expenses})
        cursor.execute(
            """SELECT category, SUM(amount) FROM transactions
               WHERE user_id = %s AND type = 'expense' AND transaction_date >= %s AND transaction_date < %s
               GROUP BY category ORDER BY SUM(amount) DESC""", (user_id, this_month, next_month)
        )
        categories = [{"category": row[0], "amount": float(row[1])} for row in cursor.fetchall()]
        cursor.execute("SELECT id, title, amount, category, type, payment_method, description, transaction_date, created_at FROM transactions WHERE user_id = %s ORDER BY transaction_date DESC, id DESC LIMIT 8", (user_id,))
        recent_transactions = [_serialize(row) for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = %s", (user_id,))
        transaction_count = cursor.fetchone()[0]
        cursor.execute("SELECT currency, savings_goal FROM financial_profiles WHERE user_id = %s", (user_id,))
        profile = cursor.fetchone()
        cursor.close()

    total_income = float(total_income)
    total_expenses = float(total_expenses)
    monthly_income = float(monthly_income)
    monthly_expenses = float(monthly_expenses)
    currency, savings_goal = (profile[0], float(profile[1])) if profile else ("INR", 0.0)
    return jsonify({
        "currency": currency,
        "totals": {"income": total_income, "expenses": total_expenses, "balance": total_income - total_expenses, "savings": total_income - total_expenses},
        "monthly": {"income": monthly_income, "expenses": monthly_expenses, "savings": monthly_income - monthly_expenses, "savings_goal": savings_goal},
        "months": months,
        "categories": categories,
        "recent_transactions": recent_transactions,
        "transaction_count": transaction_count,
    })
