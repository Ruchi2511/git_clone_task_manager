from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from bson import ObjectId
from extensions import mongo
from utils.decorators import login_required, org_admin_required, project_member_required, project_admin_required, can_manage_jobs, is_super_user
from utils.helpers import log_activity

project_bp = Blueprint("projects", __name__)

PROJECT_STATUSES = ["Planning", "Active", "On Hold", "Completed", "Archived"]


@project_bp.route("/projects")
@login_required
def project_list():
    user_id = ObjectId(session["user_id"])

    if is_super_user(session["user_id"]):
        orgs = list(mongo.db.organizations.find({}).sort("name", 1))
        projects = list(mongo.db.projects.find({"status": {"$ne": "Archived"}}).sort("updated_at", -1))
    else:
        orgs = list(mongo.db.organizations.find({"members.user_id": user_id}))
        org_ids = [org["_id"] for org in orgs]
        projects = list(mongo.db.projects.find({
            "$or": [
                {"members": user_id},
                {"created_by": user_id},
                {"organization_id": {"$in": org_ids}}
            ],
            "status": {"$ne": "Archived"}
        }).sort("updated_at", -1))

    return render_template("projects/project_list.html", projects=projects, orgs=orgs)


@project_bp.route("/organizations/<org_id>/projects/create", methods=["GET", "POST"])
@login_required
@org_admin_required
def create_project(org_id):
    org = mongo.db.organizations.find_one({"_id": ObjectId(org_id)})

    if not org:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "Active").strip()
        deadline_raw = request.form.get("deadline", "").strip()

        if not name:
            flash("Project name is required.", "error")
            return redirect(url_for("projects.create_project", org_id=org_id))

        if status not in PROJECT_STATUSES:
            status = "Active"

        deadline = None
        if deadline_raw:
            try:
                deadline = datetime.strptime(deadline_raw, "%Y-%m-%d")
            except ValueError:
                flash("Invalid deadline format.", "error")
                return redirect(url_for("projects.create_project", org_id=org_id))

        user_id = ObjectId(session["user_id"])

        project = {
            "organization_id": ObjectId(org_id),
            "name": name,
            "description": description,
            "created_by": user_id,
            "members": [user_id],
            "status": status,
            "start_date": datetime.utcnow(),
            "deadline": deadline,
            "progress": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = mongo.db.projects.insert_one(project)

        log_activity(
            org_id,
            session["user_id"],
            f"Created project '{name}'",
            "project",
            str(result.inserted_id),
            str(result.inserted_id)
        )

        flash("Project created successfully.", "success")
        return redirect(url_for("projects.project_detail", project_id=str(result.inserted_id)))

    members = []
    for member in org.get("members", []):
        user = mongo.db.users.find_one({"_id": member["user_id"]})
        if user:
            members.append(user)

    return render_template("projects/create_project.html", org=org, members=members, statuses=PROJECT_STATUSES)


@project_bp.route("/projects/<project_id>")
@login_required
@project_member_required
def project_detail(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})

    if not project:
        abort(404)

    org = mongo.db.organizations.find_one({"_id": project["organization_id"]})
    current_is_admin = can_manage_jobs(project["organization_id"], session["user_id"])

    job_filter = {"project_id": ObjectId(project_id)}
    status_filter = request.args.get("status", "").strip()
    priority_filter = request.args.get("priority", "").strip()
    assigned_filter = request.args.get("assigned_to", "").strip()
    if status_filter:
        job_filter["status"] = status_filter
    if priority_filter:
        job_filter["priority"] = priority_filter
    if assigned_filter:
        try:
            job_filter["assigned_to"] = ObjectId(assigned_filter)
        except Exception:
            pass

    tasks = list(mongo.db.tasks.find(job_filter).sort("due_date", 1))
    activities = list(mongo.db.activity_logs.find({"project_id": ObjectId(project_id)}).sort("created_at", -1).limit(15))

    member_users = []
    for member_id in project.get("members", []):
        user = mongo.db.users.find_one({"_id": member_id})
        if user:
            member_users.append(user)

    org_members = []
    if org:
        for member in org.get("members", []):
            user = mongo.db.users.find_one({"_id": member["user_id"]})
            if user:
                org_members.append(user)

    task_stats = {
        "total": len(tasks),
        "todo": len([t for t in tasks if t.get("status") == "To Do"]),
        "progress": len([t for t in tasks if t.get("status") == "In Progress"]),
        "review": len([t for t in tasks if t.get("status") == "Review"]),
        "done": len([t for t in tasks if t.get("status") == "Done"]),
    }

    return render_template(
        "projects/project_detail.html",
        project=project,
        org=org,
        tasks=tasks,
        activities=activities,
        member_users=member_users,
        org_members=org_members,
        current_is_admin=current_is_admin,
        task_stats=task_stats,
        selected_status=status_filter,
        selected_priority=priority_filter,
        selected_assigned=assigned_filter,
        now=datetime.utcnow()
    )


@project_bp.route("/projects/<project_id>/edit", methods=["GET", "POST"])
@login_required
@project_admin_required
def edit_project(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})

    if not project:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "Active").strip()
        deadline_raw = request.form.get("deadline", "").strip()

        if not name:
            flash("Project name is required.", "error")
            return redirect(url_for("projects.edit_project", project_id=project_id))

        if status not in PROJECT_STATUSES:
            status = "Active"

        deadline = None
        if deadline_raw:
            try:
                deadline = datetime.strptime(deadline_raw, "%Y-%m-%d")
            except ValueError:
                flash("Invalid deadline format.", "error")
                return redirect(url_for("projects.edit_project", project_id=project_id))

        mongo.db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {
                "name": name,
                "description": description,
                "status": status,
                "deadline": deadline,
                "updated_at": datetime.utcnow()
            }}
        )

        log_activity(project["organization_id"], session["user_id"], f"Updated project '{name}'", "project", project_id, project_id)

        flash("Project updated successfully.", "success")
        return redirect(url_for("projects.project_detail", project_id=project_id))

    return render_template("projects/edit_project.html", project=project, statuses=PROJECT_STATUSES)


@project_bp.route("/projects/<project_id>/members/add", methods=["POST"])
@login_required
@project_admin_required
def add_project_member(project_id):
    user_id = request.form.get("user_id", "").strip()
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})

    if not user_id or not project:
        abort(404)

    user_obj_id = ObjectId(user_id)

    org_member = mongo.db.organizations.find_one({
        "_id": project["organization_id"],
        "members.user_id": user_obj_id
    })

    if not org_member:
        flash("This user must be added to the organization first.", "error")
        return redirect(url_for("projects.project_detail", project_id=project_id))

    if user_obj_id in project.get("members", []):
        flash("User is already a project member.", "error")
        return redirect(url_for("projects.project_detail", project_id=project_id))

    mongo.db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$addToSet": {"members": user_obj_id}, "$set": {"updated_at": datetime.utcnow()}}
    )

    user = mongo.db.users.find_one({"_id": user_obj_id})
    log_activity(project["organization_id"], session["user_id"], f"Added {user['name']} to project", "user", user_id, project_id)

    flash("Project member added successfully.", "success")
    return redirect(url_for("projects.project_detail", project_id=project_id))


@project_bp.route("/projects/<project_id>/members/remove", methods=["POST"])
@login_required
@project_admin_required
def remove_project_member(project_id):
    user_id = request.form.get("user_id", "").strip()
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})

    if not user_id or not project:
        abort(404)

    if str(project.get("created_by")) == user_id:
        flash("Project creator cannot be removed.", "error")
        return redirect(url_for("projects.project_detail", project_id=project_id))

    mongo.db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$pull": {"members": ObjectId(user_id)}, "$set": {"updated_at": datetime.utcnow()}}
    )

    flash("Project member removed successfully.", "success")
    return redirect(url_for("projects.project_detail", project_id=project_id))


@project_bp.route("/projects/<project_id>/archive", methods=["POST"])
@login_required
@project_admin_required
def archive_project(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})

    if not project:
        abort(404)

    mongo.db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"status": "Archived", "updated_at": datetime.utcnow()}}
    )

    log_activity(project["organization_id"], session["user_id"], f"Archived project '{project['name']}'", "project", project_id, project_id)

    flash("Project archived successfully.", "success")
    return redirect(url_for("organizations.org_detail", org_id=str(project["organization_id"])))
