from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request, session

from .database import connection


profiles_bp = Blueprint("profiles", __name__)


def _authenticated_user_id():
    return session.get("user_id")


@profiles_bp.route("/me", methods=["GET", "PUT"])
def profile():
    user_id = _authenticated_user_id()
    if not user_id:
        return jsonify({"error": "Authentication is required."}), 401
    with connection() as conn:
        cursor = conn.cursor(dictionary=True)
        if request.method == "GET":
            cursor.execute("SELECT currency, monthly_income, savings_goal FROM financial_profiles WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            cursor.close()
            if result is None:
                return jsonify({"error": "Financial profile not found."}), 404
            return jsonify({"profile": {"currency": result["currency"], "monthly_income": float(result["monthly_income"]), "savings_goal": float(result["savings_goal"])}})

        data = request.get_json(silent=True) or {}
        currency = data.get("currency", "INR")
        if not isinstance(currency, str) or currency not in {"INR", "USD", "EUR", "GBP"}:
            return jsonify({"error": "Choose a supported currency.", "field_errors": {"currency": "Choose a supported currency."}}), 400
        values = {}
        for key in ("monthly_income", "savings_goal"):
            try:
                value = Decimal(str(data.get(key, 0)))
                if not value.is_finite() or value < 0 or value > Decimal("999999999.99"):
                    raise InvalidOperation
                values[key] = value.quantize(Decimal("0.01"))
            except (InvalidOperation, ValueError, TypeError):
                cursor.close()
                return jsonify({"error": "Enter non-negative amounts up to 999,999,999.99.", "field_errors": {key: "Enter a valid non-negative amount."}}), 400
        cursor.execute("UPDATE financial_profiles SET currency = %s, monthly_income = %s, savings_goal = %s WHERE user_id = %s", (currency, values["monthly_income"], values["savings_goal"], user_id))
        conn.commit()
        cursor.close()
    return jsonify({"profile": {"currency": currency, "monthly_income": float(values["monthly_income"]), "savings_goal": float(values["savings_goal"])}})
