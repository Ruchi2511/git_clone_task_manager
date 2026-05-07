from flask import Flask, render_template, request, redirect, url_for, session
from config import Config
from extensions import mongo, bcrypt, cors
from utils.session_manager import is_login_session_valid

from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.organization_routes import organization_bp
from routes.project_routes import project_bp
from routes.task_routes import task_bp
from routes.portal_routes import portal_bp
from routes.profile_routes import profile_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mongo.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(organization_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(profile_bp)

    @app.before_request
    def validate_active_login_session():
        public_endpoints = {
            "landing",
            "auth.login",
            "auth.signup",
            "auth.logout",
            "auth.session_check",
            "static"
        }

        endpoint = request.endpoint
        if not endpoint or endpoint in public_endpoints or endpoint.startswith("static"):
            return None

        if session.get("user_id") and session.get("login_token"):
            if is_login_session_valid(session.get("user_id"), session.get("login_token")):
                return None

        session.clear()
        return redirect(url_for("auth.login", next=request.path))

    @app.after_request
    def add_no_cache_headers(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.route("/")
    def landing():
        return render_template("landing.html")

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("403.html"), 403

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=False)