from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from mysql.connector import IntegrityError

from .database import connection
from .validation import normalize_email, validate_password, validate_registration


auth_bp = Blueprint("auth", __name__)


def _user(row):
    return {"id": row[0], "name": row[1], "email": row[2], "created_at": row[3].isoformat()}


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    errors = validate_registration(data)
    if errors:
        return jsonify({"error": "Please check the highlighted fields.", "field_errors": errors}), 400
    name = data["name"].strip()
    email = normalize_email(data["email"])
    password_hash = generate_password_hash(data["password"], method="scrypt")

    try:
        with connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)", (name, email, password_hash))
                user_id = cursor.lastrowid
                cursor.execute("INSERT INTO financial_profiles (user_id) VALUES (%s)", (user_id,))
                cursor.execute("SELECT id, full_name, email, created_at FROM users WHERE id = %s", (user_id,))
                row = cursor.fetchone()
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    except IntegrityError:
        return jsonify({"error": "An account with this email already exists."}), 409

    session.clear()
    session["user_id"] = user_id
    session.permanent = True
    return jsonify({"user": _user(row)}), 201


@auth_bp.post("/login")
def login():
    session.clear()
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email"))
    password = data.get("password", "")
    if not email or not isinstance(password, str) or not password:
        return jsonify({"error": "Enter your email and password."}), 400
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, email, created_at, password_hash FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        cursor.close()
    if row is None or not check_password_hash(row[4], password):
        return jsonify({"error": "Email or password is incorrect."}), 401
    session.clear()
    session["user_id"] = row[0]
    session.permanent = True
    return jsonify({"user": _user(row)})


@auth_bp.post("/logout")
def logout():
    session.clear()
    response = jsonify({"message": "You have been logged out."})
    response.delete_cookie(current_app.config.get("SESSION_COOKIE_NAME", "session"), path="/")
    return response


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication is required."}), 401
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, email, created_at FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
    if row is None:
        session.clear()
        return jsonify({"error": "Authentication is required."}), 401
    return jsonify({"user": _user(row)})


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email"))
    if len(email) > 254 or not email:
        return jsonify({"error": "Enter a valid email address.", "field_errors": {"email": "Enter a valid email address."}}), 400
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=current_app.config["RESET_TOKEN_TTL_MINUTES"])
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE user_id = %s AND used_at IS NULL", (row[0],))
            cursor.execute("INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)", (row[0], token_hash, expires_at))
            conn.commit()
        cursor.close()
    payload = {"message": "If an account exists for that email, reset instructions are ready."}
    if row and current_app.config["DEBUG"] and current_app.config["DEMO_RESET_MODE"]:
        payload["demo_reset_token"] = token
        payload["demo_note"] = "Development demo only: use this one-time token to set a new password. It expires soon."
    return jsonify(payload)


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    password = data.get("password", "")
    if not isinstance(token, str) or len(token) < 32:
        return jsonify({"error": "Enter a valid reset token."}), 400
    if not validate_password(password):
        return jsonify({"error": "Use a password between 8 and 128 characters.", "field_errors": {"password": "Use a password between 8 and 128 characters."}}), 400
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id FROM password_reset_tokens WHERE token_hash = %s AND used_at IS NULL AND expires_at > UTC_TIMESTAMP()", (token_hash,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return jsonify({"error": "That reset token is invalid or has expired."}), 400
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (generate_password_hash(password, method="scrypt"), row[1]))
        cursor.execute("UPDATE password_reset_tokens SET used_at = UTC_TIMESTAMP() WHERE id = %s", (row[0],))
        conn.commit()
        cursor.close()
    return jsonify({"message": "Your password has been updated. You can now log in."})
