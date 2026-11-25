from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request, session

from .database import connection
from .calculations import budget_progress


budgets_bp = Blueprint("budgets", __name__)
MAX_AMOUNT = Decimal("999999999.99")


@budgets_bp.route("", methods=["GET", "PUT", "DELETE"])
def budgets():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication is required."}), 401
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        month_start = date.fromisoformat(f"{month}-01")
        if month_start.strftime("%Y-%m") != month:
            raise ValueError
        next_month = date(month_start.year + (month_start.month == 12), month_start.month % 12 + 1, 1)
    except ValueError:
        return jsonify({"error": "Choose a valid budget month in YYYY-MM format."}), 400

    if request.method == "GET":
        with connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT b.category, b.amount, COALESCE(SUM(t.amount),0)
                   FROM monthly_budgets b LEFT JOIN transactions t
                     ON t.user_id = b.user_id AND t.category = b.category AND t.type = 'expense'
                     AND t.transaction_date >= %s AND t.transaction_date < %s
                   WHERE b.user_id = %s AND b.month = %s
                   GROUP BY b.category, b.amount ORDER BY b.category""",
                (month_start, next_month, user_id, month),
            )
            result = []
            for row in cursor.fetchall():
                budget = {"category": row[0], "limit": float(row[1]), "spent": float(row[2])}
                budget.update(budget_progress(row[1], row[2]))
                result.append(budget)
            cursor.close()
        return jsonify({"month": month, "budgets": result})

    data = request.get_json(silent=True) or {}
    category = data.get("category", "")
    if not isinstance(category, str) or not 1 <= len(category.strip()) <= 60:
        return jsonify({"error": "Enter a category between 1 and 60 characters.", "field_errors": {"category": "Enter a valid category."}}), 400
    category = category.strip()
    if request.method == "DELETE":
        with connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM monthly_budgets WHERE user_id = %s AND category = %s AND month = %s", (user_id, category, month))
            deleted = cursor.rowcount
            conn.commit()
            cursor.close()
        if not deleted:
            return jsonify({"error": "Budget not found."}), 404
        return jsonify({"message": "Budget removed."})

    try:
        amount = Decimal(str(data.get("limit", "")))
        if not amount.is_finite() or amount < 0 or amount > MAX_AMOUNT:
            raise InvalidOperation
        amount = amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return jsonify({"error": "Enter a non-negative budget up to 999,999,999.99.", "field_errors": {"limit": "Enter a valid budget amount."}}), 400
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO monthly_budgets (user_id, category, month, amount) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE amount = VALUES(amount)",
            (user_id, category, month, amount),
        )
        conn.commit()
        cursor.close()
    return jsonify({"budget": {"category": category, "month": month, "limit": float(amount)}}), 201
