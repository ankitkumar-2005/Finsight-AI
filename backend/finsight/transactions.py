from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request, session

from .database import connection


transactions_bp = Blueprint("transactions", __name__)
PAYMENT_METHODS = {"cash", "debit_card", "credit_card", "bank_transfer", "digital_wallet", "other"}
SORT_COLUMNS = {"date": "transaction_date", "title": "title", "amount": "amount", "category": "category", "type": "type"}
MAX_AMOUNT = Decimal("999999999.99")


def _error(message, status=400, field=None):
    payload = {"error": message}
    if field:
        payload["field_errors"] = {field: message}
    return jsonify(payload), status


def _valid_data(data):
    errors = {}
    title = data.get("title")
    category = data.get("category")
    transaction_type = data.get("type")
    payment_method = data.get("payment_method")
    description = data.get("description", "")
    raw_date = data.get("transaction_date")
    try:
        amount = Decimal(str(data.get("amount", "")))
        if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
            raise InvalidOperation
        amount = amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        errors["amount"] = "Enter an amount greater than zero and no more than 999,999,999.99."
        amount = None
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        errors["title"] = "Enter a title between 1 and 120 characters."
    if not isinstance(category, str) or not 1 <= len(category.strip()) <= 60:
        errors["category"] = "Enter a category between 1 and 60 characters."
    if not isinstance(transaction_type, str) or transaction_type not in {"income", "expense"}:
        errors["type"] = "Choose income or expense."
    if not isinstance(payment_method, str) or payment_method not in PAYMENT_METHODS:
        errors["payment_method"] = "Choose a valid payment method."
    if not isinstance(description, str) or len(description) > 500:
        errors["description"] = "Description must be 500 characters or fewer."
    try:
        if not isinstance(raw_date, str) or date.fromisoformat(raw_date).isoformat() != raw_date:
            raise ValueError
        transaction_date = raw_date
    except (ValueError, TypeError):
        errors["transaction_date"] = "Choose a valid transaction date."
        transaction_date = None
    return errors, {
        "title": title.strip() if isinstance(title, str) else "",
        "amount": amount,
        "category": category.strip() if isinstance(category, str) else "",
        "type": transaction_type,
        "payment_method": payment_method,
        "description": description.strip() if isinstance(description, str) else "",
        "transaction_date": transaction_date,
    }


def _serialize(row):
    return {
        "id": row[0], "title": row[1], "amount": float(row[2]), "category": row[3],
        "type": row[4], "payment_method": row[5], "description": row[6] or "",
        "transaction_date": row[7].isoformat(), "created_at": row[8].isoformat() if row[8] else None,
    }


def _current_user():
    return session.get("user_id")


@transactions_bp.get("")
def list_transactions():
    user_id = _current_user()
    if not user_id:
        return _error("Authentication is required.", 401)
    args = request.args
    transaction_type = args.get("type", "").lower()
    category = args.get("category", "").strip()
    search = args.get("q", "").strip()
    if transaction_type and transaction_type not in {"income", "expense"}:
        return _error("Choose income or expense.", field="type")
    if len(category) > 60 or len(search) > 120:
        return _error("Search and category filters are too long.")

    dates = {}
    for key in ("date_from", "date_to"):
        value = args.get(key)
        if value:
            try:
                dates[key] = date.fromisoformat(value)
            except ValueError:
                return _error(f"{key.replace('_', ' ').capitalize()} must be a valid date.", field=key)
    if dates.get("date_from") and dates.get("date_to") and dates["date_from"] > dates["date_to"]:
        return _error("Start date must be before end date.", field="date_from")

    sort_by = args.get("sort_by", "date")
    direction = args.get("sort_dir", "desc").lower()
    if sort_by not in SORT_COLUMNS or direction not in {"asc", "desc"}:
        return _error("Choose a valid sort order.")
    clauses = ["user_id = %s"]
    values = [user_id]
    if transaction_type:
        clauses.append("type = %s"); values.append(transaction_type)
    if category:
        clauses.append("category = %s"); values.append(category)
    if dates.get("date_from"):
        clauses.append("transaction_date >= %s"); values.append(dates["date_from"])
    if dates.get("date_to"):
        clauses.append("transaction_date <= %s"); values.append(dates["date_to"])
    if search:
        clauses.append("(title LIKE %s OR description LIKE %s OR category LIKE %s)")
        pattern = f"%{search}%"; values.extend([pattern, pattern, pattern])

    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, title, amount, category, type, payment_method, description, transaction_date, created_at FROM transactions WHERE {' AND '.join(clauses)} ORDER BY {SORT_COLUMNS[sort_by]} {direction.upper()}, id DESC LIMIT 500",
            tuple(values),
        )
        rows = [_serialize(row) for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT category FROM transactions WHERE user_id = %s ORDER BY category", (user_id,))
        categories = [row[0] for row in cursor.fetchall()]
        cursor.close()
    return jsonify({"transactions": rows, "categories": categories, "limit": 500})


@transactions_bp.post("")
def create_transaction():
    user_id = _current_user()
    if not user_id:
        return _error("Authentication is required.", 401)
    errors, values = _valid_data(request.get_json(silent=True) or {})
    if errors:
        return jsonify({"error": "Please check the transaction details.", "field_errors": errors}), 400
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (user_id, title, amount, category, type, payment_method, description, transaction_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, values["title"], values["amount"], values["category"], values["type"], values["payment_method"], values["description"], values["transaction_date"]),
        )
        transaction_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT id, title, amount, category, type, payment_method, description, transaction_date, created_at FROM transactions WHERE id = %s AND user_id = %s", (transaction_id, user_id))
        result = _serialize(cursor.fetchone())
        cursor.close()
    return jsonify({"transaction": result}), 201


@transactions_bp.route("/<int:transaction_id>", methods=["PUT", "DELETE"])
def update_or_delete_transaction(transaction_id):
    user_id = _current_user()
    if not user_id:
        return _error("Authentication is required.", 401)
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM transactions WHERE id = %s AND user_id = %s", (transaction_id, user_id))
        exists = cursor.fetchone()
        if not exists:
            cursor.close()
            return _error("Transaction not found.", 404)
        if request.method == "DELETE":
            cursor.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s", (transaction_id, user_id))
            conn.commit()
            cursor.close()
            return jsonify({"message": "Transaction deleted."})
        errors, values = _valid_data(request.get_json(silent=True) or {})
        if errors:
            cursor.close()
            return jsonify({"error": "Please check the transaction details.", "field_errors": errors}), 400
        cursor.execute(
            "UPDATE transactions SET title = %s, amount = %s, category = %s, type = %s, payment_method = %s, description = %s, transaction_date = %s WHERE id = %s AND user_id = %s",
            (values["title"], values["amount"], values["category"], values["type"], values["payment_method"], values["description"], values["transaction_date"], transaction_id, user_id),
        )
        conn.commit()
        cursor.execute("SELECT id, title, amount, category, type, payment_method, description, transaction_date, created_at FROM transactions WHERE id = %s AND user_id = %s", (transaction_id, user_id))
        result = _serialize(cursor.fetchone())
        cursor.close()
    return jsonify({"transaction": result})
