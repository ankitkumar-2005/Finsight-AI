from datetime import timedelta
import os

from flask import Flask, jsonify
from flask_cors import CORS
from mysql.connector import Error as MySQLError

from .auth import auth_bp
from .config import Config
from .database import close_pool, init_pool
from .profiles import profiles_bp
from .transactions import transactions_bp
from .dashboard import dashboard_bp
from .budgets import budgets_bp
from .reports import reports_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not app.config["DEBUG"],
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("FLASK_SECRET_KEY must be configured before starting the API.")

    origins = app.config["CORS_ORIGINS"]
    if origins:
        CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)

    if not app.config.get("TESTING"):
        init_pool(app.config)
        app.extensions["finsight_pool"] = True
        app.teardown_appcontext(close_pool)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(profiles_bp, url_prefix="/api/profile")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(budgets_bp, url_prefix="/api/budgets")
    app.register_blueprint(reports_bp, url_prefix="/api/analytics")
    from .ai_insights import ai_insights_bp
    app.register_blueprint(ai_insights_bp, url_prefix="/api/ai-insights")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "The requested API route was not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"error": "This method is not supported for the requested route."}), 405

    @app.errorhandler(413)
    def payload_too_large(_error):
        return jsonify({"error": "The request is too large."}), 413

    @app.errorhandler(MySQLError)
    def database_error(error):
        app.logger.exception("Database operation failed", exc_info=error)
        return jsonify({"error": "The service is temporarily unavailable. Please try again."}), 503

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unhandled API error", exc_info=error)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

    return app
