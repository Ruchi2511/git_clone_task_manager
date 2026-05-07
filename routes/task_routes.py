from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, jsonify
from bson import ObjectId
from extensions import mongo
from utils.decorators import login_required, project_admin_required, task_access_required, can_manage_jobs
from utils.helpers import log_activity, calc_project_progress

task_bp = Blueprint("tasks", __name__)

JOB_STATUSES = ["To Do", "In Progress", "Review", "Done"]
JOB_PRIORITIES = ["Low", "Medium", "High", "Critical"]


@task_bp.route("/projects/<project_id>/tasks/create", methods=["GET", "POST"])
@login_required
@project_admin_required
def create_task(project_id):
    project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})

    if not project:
        abort(404)

    member_users = []
    for member_id in project.get("members", []):
        user = mongo.db.users.find_one({"_id": member_id})
        if user:
            member_users.append(user)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        assigned_to = request.form.get("assigned_to", "").strip()
        priority = request.form.get("priority", "Medium").strip()
        status = request.form.get("status", "To Do").strip()
        due_date_raw = request.form.get("due_date", "").strip()

        if not title:
            flash("Job title is required.", "error")
            return redirect(url_for("tasks.create_task", project_id=project_id))

        if priority not in JOB_PRIORITIES:
            priority = "Medium"

        if status not in JOB_STATUSES:
            status = "To Do"

        assigned_obj_id = None
        if assigned_to:
            assigned_obj_id = ObjectId(assigned_to)
            if assigned_obj_id not in project.get("members", []):
                flash("Job can only be assigned to a project member.", "error")
                return redirect(url_for("tasks.create_task", project_id=project_id))

        due_date = None
        if due_date_raw:
            try:
                due_date = datetime.strptime(due_date_raw, "%Y-%m-%d")
            except ValueError:
                flash("Invalid due date format.", "error")
                return redirect(url_for("tasks.create_task", project_id=project_id))

        task = {
            "project_id": ObjectId(project_id),
            "organization_id": project["organization_id"],
            "title": title,
            "description": description,
            "assigned_to": assigned_obj_id,
            "created_by": ObjectId(session["user_id"]),
            "status": status,
            "priority": priority,
            "due_date": due_date,
            "comments": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = mongo.db.tasks.insert_one(task)
        calc_project_progress(project_id)
        log_activity(project["organization_id"], session["user_id"], f"Created job '{title}'", "task", str(result.inserted_id), project_id)

        flash("Job created successfully.", "success")
        return redirect(url_for("projects.project_detail", project_id=project_id))

    return render_template(
        "tasks/create_task.html",
        project=project,
        members=member_users,
        statuses=JOB_STATUSES,
        priorities=JOB_PRIORITIES
    )


@task_bp.route("/tasks/<task_id>")
@login_required
@task_access_required
def task_detail(task_id):
    task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})

    if not task:
        abort(404)

    project = mongo.db.projects.find_one({"_id": task["project_id"]})
    assigned_user = mongo.db.users.find_one({"_id": task["assigned_to"]}) if task.get("assigned_to") else None
    creator = mongo.db.users.find_one({"_id": task["created_by"]}) if task.get("created_by") else None
    current_is_admin = can_manage_jobs(task["organization_id"], session["user_id"])

    comments = []
    for comment in task.get("comments", []):
        user = mongo.db.users.find_one({"_id": comment["user_id"]})
        comments.append({
            "user": user,
            "comment": comment["comment"],
            "created_at": comment["created_at"]
        })

    return render_template(
        "tasks/task_detail.html",
        task=task,
        project=project,
        assigned_user=assigned_user,
        creator=creator,
        comments=comments,
        statuses=JOB_STATUSES,
        current_is_admin=current_is_admin,
        now=datetime.utcnow()
    )


@task_bp.route("/tasks/<task_id>/edit", methods=["GET", "POST"])
@login_required
@task_access_required
def edit_task(task_id):
    task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})

    if not task:
        abort(404)

    if not can_manage_jobs(task["organization_id"], session["user_id"]):
        abort(403)

    project = mongo.db.projects.find_one({"_id": task["project_id"]})

    member_users = []
    for member_id in project.get("members", []):
        user = mongo.db.users.find_one({"_id": member_id})
        if user:
            member_users.append(user)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        assigned_to = request.form.get("assigned_to", "").strip()
        priority = request.form.get("priority", "Medium").strip()
        status = request.form.get("status", "To Do").strip()
        due_date_raw = request.form.get("due_date", "").strip()

        if not title:
            flash("Job title is required.", "error")
            return redirect(url_for("tasks.edit_task", task_id=task_id))

        assigned_obj_id = ObjectId(assigned_to) if assigned_to else None

        if assigned_obj_id and assigned_obj_id not in project.get("members", []):
            flash("Job can only be assigned to a project member.", "error")
            return redirect(url_for("tasks.edit_task", task_id=task_id))

        if priority not in JOB_PRIORITIES:
            priority = "Medium"

        if status not in JOB_STATUSES:
            status = "To Do"

        due_date = None
        if due_date_raw:
            try:
                due_date = datetime.strptime(due_date_raw, "%Y-%m-%d")
            except ValueError:
                flash("Invalid due date format.", "error")
                return redirect(url_for("tasks.edit_task", task_id=task_id))

        mongo.db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "title": title,
                "description": description,
                "assigned_to": assigned_obj_id,
                "priority": priority,
                "status": status,
                "due_date": due_date,
                "updated_at": datetime.utcnow()
            }}
        )

        calc_project_progress(str(project["_id"]))
        log_activity(task["organization_id"], session["user_id"], f"Updated job '{title}'", "task", task_id, str(project["_id"]))

        flash("Job updated successfully.", "success")
        return redirect(url_for("tasks.task_detail", task_id=task_id))

    return render_template(
        "tasks/edit_task.html",
        task=task,
        project=project,
        members=member_users,
        statuses=JOB_STATUSES,
        priorities=JOB_PRIORITIES
    )


@task_bp.route("/tasks/<task_id>/status", methods=["POST"])
@login_required
@task_access_required
def update_task_status(task_id):
    status = request.form.get("status") or (request.json or {}).get("status")

    if status not in JOB_STATUSES:
        if request.is_json:
            return jsonify({"success": False, "message": "Invalid status"}), 400
        flash("Invalid job status.", "error")
        return redirect(url_for("tasks.task_detail", task_id=task_id))

    task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})

    mongo.db.tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}}
    )

    calc_project_progress(str(task["project_id"]))
    log_activity(task["organization_id"], session["user_id"], f"Changed job '{task['title']}' status to {status}", "task", task_id, str(task["project_id"]))

    if request.is_json:
        return jsonify({"success": True, "status": status})

    flash("Job status updated.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task_id))


@task_bp.route("/tasks/<task_id>/comment", methods=["POST"])
@login_required
@task_access_required
def add_comment(task_id):
    comment = request.form.get("comment", "").strip()

    if not comment:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("tasks.task_detail", task_id=task_id))

    task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})

    mongo.db.tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$push": {
            "comments": {
                "user_id": ObjectId(session["user_id"]),
                "comment": comment,
                "created_at": datetime.utcnow()
            }
        }, "$set": {"updated_at": datetime.utcnow()}}
    )

    log_activity(task["organization_id"], session["user_id"], f"Commented on job '{task['title']}'", "task", task_id, str(task["project_id"]))

    flash("Comment added.", "success")
    return redirect(url_for("tasks.task_detail", task_id=task_id))


@task_bp.route("/tasks/<task_id>/delete", methods=["POST"])
@login_required
@task_access_required
def delete_task(task_id):
    task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})

    if not task:
        abort(404)

    if not can_manage_jobs(task["organization_id"], session["user_id"]):
        abort(403)

    project_id = str(task["project_id"])
    mongo.db.tasks.delete_one({"_id": ObjectId(task_id)})
    calc_project_progress(project_id)
    log_activity(task["organization_id"], session["user_id"], f"Deleted job '{task['title']}'", "task", None, project_id)

    flash("Job deleted successfully.", "success")
    return redirect(url_for("projects.project_detail", project_id=project_id))
