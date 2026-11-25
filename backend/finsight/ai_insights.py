from flask import Blueprint, current_app, jsonify, session

from finsight_ai import analyze_transactions

from .database import connection


ai_insights_bp = Blueprint("ai_insights", __name__)


@ai_insights_bp.get("")
def insights():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication is required."}), 401
    try:
        with connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """SELECT id, title, amount, category, type, transaction_date
                   FROM transactions WHERE user_id = %s ORDER BY transaction_date, id""",
                (user_id,),
            )
            records = cursor.fetchall()
            cursor.close()
        return jsonify(analyze_transactions(records))
    except (ValueError, TypeError) as error:
        current_app.logger.info("AI insights input validation failed: %s", error)
        return jsonify({"error": "Financial analysis could not process the available transactions."}), 422
