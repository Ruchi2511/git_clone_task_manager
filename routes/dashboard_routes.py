from flask import Blueprint, render_template, session, request, jsonify
from bson import ObjectId
from datetime import datetime
from extensions import mongo
from utils.decorators import login_required, is_super_user
from utils.validators import to_object_id


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    user_id = ObjectId(session["user_id"])
    super_user = is_super_user(session["user_id"])

    organizations = list(mongo.db.organizations.find({}).sort("name", 1)) if super_user else list(mongo.db.organizations.find({"members.user_id": user_id}).sort("name", 1))
    org_ids = [org["_id"] for org in organizations]

    status_filter = request.args.get("status", "").strip()
    priority_filter = request.args.get("priority", "").strip()
    org_filter = request.args.get("org_id", "").strip()
    overdue_only = request.args.get("overdue") == "1"
    search = request.args.get("q", "").strip()

    job_query = {}
    if super_user:
        if org_filter:
            org_obj_id = to_object_id(org_filter)
            if org_obj_id:
                job_query["organization_id"] = org_obj_id
    else:
        job_query["$or"] = [{"assigned_to": user_id}, {"organization_id": {"$in": org_ids}}]
        if org_filter:
            org_obj_id = to_object_id(org_filter)
            if org_obj_id and org_obj_id in org_ids:
                job_query = {"organization_id": org_obj_id}

    if status_filter:
        job_query["status"] = status_filter
    if priority_filter:
        job_query["priority"] = priority_filter
    if search:
        job_query["$and"] = job_query.get("$and", []) + [{"$or": [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]}]

    jobs = list(mongo.db.tasks.find(job_query).sort("due_date", 1))
    now = datetime.utcnow()
    if overdue_only:
        jobs = [j for j in jobs if j.get("due_date") and j["due_date"] < now and j.get("status") != "Done"]

    total_jobs = len(jobs)
    completed_jobs = len([j for j in jobs if j.get("status") == "Done"])
    in_progress_jobs = len([j for j in jobs if j.get("status") == "In Progress"])
    overdue_jobs = [j for j in jobs if j.get("due_date") and j["due_date"] < now and j.get("status") != "Done"]

    status_counts = {s: len([j for j in jobs if j.get("status") == s]) for s in ["To Do", "In Progress", "Review", "Done"]}
    priority_counts = {p: len([j for j in jobs if j.get("priority") == p]) for p in ["Low", "Medium", "High", "Critical"]}

    user_counts = {}
    for job in jobs:
        assignee = "Unassigned"
        if job.get("assigned_to"):
            user = mongo.db.users.find_one({"_id": job["assigned_to"]})
            assignee = user["name"] if user else "Unknown"
        user_counts[assignee] = user_counts.get(assignee, 0) + 1

    recent_activities = list(mongo.db.activity_logs.find({}).sort("created_at", -1).limit(15)) if super_user else list(mongo.db.activity_logs.find({"organization_id": {"$in": org_ids}}).sort("created_at", -1).limit(15))

    return render_template(
        "dashboard/dashboard.html",
        organizations=organizations,
        assigned_tasks=jobs,
        total_tasks=total_jobs,
        completed_tasks=completed_jobs,
        in_progress_tasks=in_progress_jobs,
        overdue_tasks=overdue_jobs,
        status_counts=status_counts,
        priority_counts=priority_counts,
        user_counts=user_counts,
        recent_activities=recent_activities,
        super_user=super_user,
        selected_status=status_filter,
        selected_priority=priority_filter,
        selected_org=org_filter,
        overdue_only=overdue_only,
        search=search,
        now=now
    )


@dashboard_bp.route("/api/dashboard/stats")
@login_required
def dashboard_stats_api():
    user_id = ObjectId(session["user_id"])
    super_user = is_super_user(session["user_id"])
    if super_user:
        jobs = list(mongo.db.tasks.find({}))
    else:
        orgs = list(mongo.db.organizations.find({"members.user_id": user_id}))
        org_ids = [org["_id"] for org in orgs]
        jobs = list(mongo.db.tasks.find({"$or": [{"assigned_to": user_id}, {"organization_id": {"$in": org_ids}}]}))

    return jsonify({
        "total_jobs": len(jobs),
        "done": len([j for j in jobs if j.get("status") == "Done"]),
        "in_progress": len([j for j in jobs if j.get("status") == "In Progress"]),
        "overdue": len([j for j in jobs if j.get("due_date") and j["due_date"] < datetime.utcnow() and j.get("status") != "Done"])
    })
