from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from bson import ObjectId
from datetime import datetime
from extensions import mongo
from utils.decorators import login_required, org_member_required, org_admin_required, get_org_role, can_manage_org, ORG_ROLES, super_user_required
from utils.validators import to_object_id
from utils.helpers import log_activity

organization_bp = Blueprint("organizations", __name__)


@organization_bp.route("/organizations/create", methods=["GET", "POST"])
@login_required
@super_user_required
def create_org():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Organization name is required.", "error")
            return redirect(url_for("organizations.create_org"))

        user_id = ObjectId(session["user_id"])
        org = {
            "name": name,
            "description": description,
            "created_by": user_id,
            "members": [],
            "settings": {
                "allow_team_leads_create_jobs": True,
                "default_job_status": "To Do",
                "default_priority": "Medium"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = mongo.db.organizations.insert_one(org)
        log_activity(result.inserted_id, session["user_id"], f"Created organization '{name}'", "organization", str(result.inserted_id), None)
        flash("Organization created successfully. Add members from the organization page or Super User portal.", "success")
        return redirect(url_for("organizations.org_detail", org_id=str(result.inserted_id)))

    return render_template("organizations/create_org.html")


@organization_bp.route("/organizations/<org_id>")
@login_required
@org_member_required
def org_detail(org_id):
    org_obj_id = to_object_id(org_id)
    if not org_obj_id:
        abort(404)
    org = mongo.db.organizations.find_one({"_id": org_obj_id})
    if not org:
        abort(404)

    members = []
    for member in org.get("members", []):
        user = mongo.db.users.find_one({"_id": member["user_id"]})
        if user:
            members.append({"id": str(user["_id"]), "name": user["name"], "email": user["email"], "role": member["role"], "joined_at": member["joined_at"]})

    projects = list(mongo.db.projects.find({"organization_id": org_obj_id}))
    jobs = list(mongo.db.tasks.find({"organization_id": org_obj_id}))
    activities = list(mongo.db.activity_logs.find({"organization_id": org_obj_id}).sort("created_at", -1).limit(15))
    current_role = get_org_role(org_id, session["user_id"])
    current_can_manage_org = can_manage_org(org_id, session["user_id"])

    return render_template(
        "organizations/org_detail.html",
        org=org,
        members=members,
        projects=projects,
        jobs=jobs,
        activities=activities,
        current_role=current_role or session.get("portal_role"),
        current_can_manage_org=current_can_manage_org,
        roles=ORG_ROLES
    )


@organization_bp.route("/organizations/<org_id>/config", methods=["GET", "POST"])
@login_required
@org_admin_required
def org_config(org_id):
    org_obj_id = to_object_id(org_id)
    if not org_obj_id:
        abort(404)
    org = mongo.db.organizations.find_one({"_id": org_obj_id})
    if not org:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        allow_team_leads = request.form.get("allow_team_leads_create_jobs") == "on"
        default_priority = request.form.get("default_priority", "Medium")

        if not name:
            flash("Organization name is required.", "error")
            return redirect(url_for("organizations.org_config", org_id=org_id))

        if default_priority not in ["Low", "Medium", "High", "Critical"]:
            default_priority = "Medium"

        mongo.db.organizations.update_one(
            {"_id": org_obj_id},
            {"$set": {
                "name": name,
                "description": description,
                "settings.allow_team_leads_create_jobs": allow_team_leads,
                "settings.default_priority": default_priority,
                "updated_at": datetime.utcnow()
            }}
        )
        log_activity(org_id, session["user_id"], f"Updated organization config for '{name}'", "organization", org_id, None)
        flash("Organization configuration updated.", "success")
        return redirect(url_for("organizations.org_detail", org_id=org_id))

    return render_template("organizations/org_config.html", org=org)


@organization_bp.route("/organizations/<org_id>/members/add", methods=["POST"])
@login_required
@org_admin_required
def add_member(org_id):
    email = request.form.get("email", "").strip().lower()
    role = request.form.get("role", "Member").strip()
    if role not in ORG_ROLES:
        role = "Member"

    user = mongo.db.users.find_one({"email": email})
    if not user:
        flash("No portal user found with this email. A Super User must create the portal account first.", "error")
        return redirect(url_for("organizations.org_detail", org_id=org_id))

    org_obj_id = to_object_id(org_id)
    if not org_obj_id:
        abort(404)

    if mongo.db.organizations.find_one({"_id": org_obj_id, "members.user_id": user["_id"]}):
        flash("User is already a member of this organization.", "error")
        return redirect(url_for("organizations.org_detail", org_id=org_id))

    mongo.db.organizations.update_one(
        {"_id": org_obj_id},
        {"$push": {"members": {"user_id": user["_id"], "role": role, "joined_at": datetime.utcnow()}}, "$set": {"updated_at": datetime.utcnow()}}
    )
    log_activity(org_id, session["user_id"], f"Added {user['name']} as {role}", "user", str(user["_id"]), None)
    flash("Organization member added successfully.", "success")
    return redirect(url_for("organizations.org_detail", org_id=org_id))


@organization_bp.route("/organizations/<org_id>/members/update-role", methods=["POST"])
@login_required
@org_admin_required
def update_member_role(org_id):
    user_obj_id = to_object_id(request.form.get("user_id"))
    role = request.form.get("role", "Member")
    if not user_obj_id:
        abort(404)
    if role not in ORG_ROLES:
        role = "Member"

    mongo.db.organizations.update_one(
        {"_id": ObjectId(org_id), "members.user_id": user_obj_id},
        {"$set": {"members.$.role": role, "updated_at": datetime.utcnow()}}
    )
    flash("Member role updated.", "success")
    return redirect(url_for("organizations.org_detail", org_id=org_id))


@organization_bp.route("/organizations/<org_id>/members/remove", methods=["POST"])
@login_required
@org_admin_required
def remove_member(org_id):
    user_obj_id = to_object_id(request.form.get("user_id"))
    if not user_obj_id:
        flash("Invalid user.", "error")
        return redirect(url_for("organizations.org_detail", org_id=org_id))

    mongo.db.organizations.update_one(
        {"_id": ObjectId(org_id)},
        {"$pull": {"members": {"user_id": user_obj_id}}, "$set": {"updated_at": datetime.utcnow()}}
    )
    mongo.db.projects.update_many({"organization_id": ObjectId(org_id)}, {"$pull": {"members": user_obj_id}})
    flash("Member removed from organization and related projects.", "success")
    return redirect(url_for("organizations.org_detail", org_id=org_id))
