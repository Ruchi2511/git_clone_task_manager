from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from datetime import datetime
from extensions import mongo, bcrypt
from utils.validators import is_valid_email
from utils.session_manager import create_login_session, close_login_session, is_login_session_valid


auth_bp = Blueprint("auth", __name__)


def set_secure_login_session(user):
    session.permanent = True
    session["user_id"] = str(user["_id"])
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    session["portal_role"] = user.get("portal_role", "User")
    session["login_token"] = create_login_session(
        user["_id"],
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.remote_addr
    )


def no_store_response(payload):
    response = make_response(payload)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Signup is only used to create the first Super User."""
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard"))

    users_count = mongo.db.users.count_documents({})
    if users_count > 0:
        flash("Portal signup is closed. Ask a Super User to create your account.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not name or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return redirect(url_for("auth.signup"))

        if not is_valid_email(email):
            flash("Enter a valid email address.", "error")
            return redirect(url_for("auth.signup"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.signup"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("auth.signup"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        user = {
            "name": name,
            "email": email,
            "password": hashed_password,
            "portal_role": "Super User",
            "avatar": None,
            "created_by": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True
        }

        result = mongo.db.users.insert_one(user)

        created_user = mongo.db.users.find_one({"_id": result.inserted_id})
        set_secure_login_session(created_user)

        flash("Super User account created successfully.", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/signup.html", first_user=True)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        if is_login_session_valid(session.get("user_id"), session.get("login_token")):
            return redirect(url_for("dashboard.dashboard"))
        session.clear()

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("auth.login"))

        user = mongo.db.users.find_one({"email": email})

        if not user or not bcrypt.check_password_hash(user["password"], password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("auth.login"))

        if not user.get("is_active", True):
            flash("This account is inactive. Contact a Super User.", "error")
            return redirect(url_for("auth.login"))

        set_secure_login_session(user)

        flash("Logged in successfully.", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("dashboard.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    close_login_session(session.get("user_id"), session.get("login_token"))
    session.clear()
    flash("You have been logged out.", "success")
    response = redirect(url_for("auth.login"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.delete_cookie("session")
    return response


@auth_bp.route("/auth/session-check")
def session_check():
    valid = is_login_session_valid(session.get("user_id"), session.get("login_token"))
    if not valid:
        session.clear()
    return no_store_response(jsonify({"authenticated": valid}))
