from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from bson import ObjectId
from extensions import mongo, bcrypt
from utils.decorators import login_required, super_user_required, ORG_ROLES
from utils.validators import is_valid_email, to_object_id
from utils.helpers import log_activity

portal_bp = Blueprint("portal", __name__)


@portal_bp.route("/portal/users")
@login_required
@super_user_required
def users():
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "all")

    filters = {}
    if query:
        filters["$or"] = [
            {"name": {"$regex": query, "$options": "i"}},
            {"email": {"$regex": query, "$options": "i"}}
        ]
    if status == "active":
        filters["is_active"] = True
    elif status == "inactive":
        filters["is_active"] = False

    users = list(mongo.db.users.find(filters).sort("created_at", -1))
    organizations = list(mongo.db.organizations.find({}).sort("name", 1))

    return render_template("portal/users.html", users=users, organizations=organizations, roles=ORG_ROLES, query=query, status=status)


@portal_bp.route("/portal/users/create", methods=["GET", "POST"])
@login_required
@super_user_required
def create_user():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        portal_role = request.form.get("portal_role", "User").strip()

        if not name or not email or not password:
            flash("Name, email, and password are required.", "error")
            return redirect(url_for("portal.create_user"))

        if not is_valid_email(email):
            flash("Enter a valid email address.", "error")
            return redirect(url_for("portal.create_user"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("portal.create_user"))

        if portal_role not in ["User", "Super User"]:
            portal_role = "User"

        if mongo.db.users.find_one({"email": email}):
            flash("A portal user with this email already exists.", "error")
            return redirect(url_for("portal.create_user"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        result = mongo.db.users.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "portal_role": portal_role,
            "avatar": None,
            "created_by": ObjectId(session["user_id"]),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True
        })

        mongo.db.activity_logs.insert_one({
            "organization_id": None,
            "project_id": None,
            "user_id": ObjectId(session["user_id"]),
            "action": f"Created portal user '{name}'",
            "target_type": "user",
            "target_id": result.inserted_id,
            "created_at": datetime.utcnow()
        })

        flash("Portal user created successfully.", "success")
        return redirect(url_for("portal.users"))

    return render_template("portal/create_user.html")


@portal_bp.route("/portal/users/<user_id>/toggle", methods=["POST"])
@login_required
@super_user_required
def toggle_user(user_id):
    user_obj_id = to_object_id(user_id)
    if not user_obj_id:
        abort(404)

    user = mongo.db.users.find_one({"_id": user_obj_id})
    if not user:
        abort(404)

    if str(user["_id"]) == session["user_id"]:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("portal.users"))

    mongo.db.users.update_one({"_id": user_obj_id}, {"$set": {"is_active": not user.get("is_active", True), "updated_at": datetime.utcnow()}})
    flash("Portal user status updated.", "success")
    return redirect(url_for("portal.users"))


@portal_bp.route("/portal/orgs/<org_id>/members/add", methods=["POST"])
@login_required
@super_user_required
def add_user_to_org(org_id):
    org_obj_id = to_object_id(org_id)
    user_obj_id = to_object_id(request.form.get("user_id"))
    role = request.form.get("role", "Member")

    if not org_obj_id or not user_obj_id:
        abort(404)
    if role not in ORG_ROLES:
        role = "Member"

    org = mongo.db.organizations.find_one({"_id": org_obj_id})
    user = mongo.db.users.find_one({"_id": user_obj_id})
    if not org or not user:
        abort(404)

    if mongo.db.organizations.find_one({"_id": org_obj_id, "members.user_id": user_obj_id}):
        flash("User is already a member of this organization.", "error")
        return redirect(url_for("portal.users"))

    mongo.db.organizations.update_one(
        {"_id": org_obj_id},
        {"$push": {"members": {"user_id": user_obj_id, "role": role, "joined_at": datetime.utcnow()}}, "$set": {"updated_at": datetime.utcnow()}}
    )
    log_activity(org_id, session["user_id"], f"Super User added {user['name']} as {role}", "user", str(user_obj_id), None)
    flash("User added to organization.", "success")
    return redirect(url_for("organizations.org_detail", org_id=org_id))
