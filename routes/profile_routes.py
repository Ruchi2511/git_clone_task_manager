from flask import Blueprint, render_template, session, abort
from bson import ObjectId
from datetime import datetime
from extensions import mongo
from utils.decorators import login_required, is_super_user

profile_bp = Blueprint("profile", __name__)


def _safe_date(value):
    return value if value else None


@profile_bp.route("/profile")
@login_required
def profile():
    user_id = ObjectId(session["user_id"])
    user = mongo.db.users.find_one({"_id": user_id})

    if not user:
        abort(404)

    super_user = is_super_user(str(user_id))

    organizations = list(mongo.db.organizations.find({
        "members.user_id": user_id
    }).sort("name", 1))

    org_cards = []
    org_ids = []
    for org in organizations:
        role = "Member"
        for member in org.get("members", []):
            if str(member.get("user_id")) == str(user_id):
                role = member.get("role", "Member")
                break
        org_ids.append(org["_id"])
        org_cards.append({
            "_id": org["_id"],
            "name": org.get("name", "Organization"),
            "description": org.get("description", ""),
            "role": role,
            "created_at": _safe_date(org.get("created_at"))
        })

    assigned_jobs = list(mongo.db.tasks.find({
        "assigned_to": user_id
    }).sort("due_date", 1))

    now = datetime.utcnow()
    completed_jobs = [job for job in assigned_jobs if job.get("status") == "Done"]
    active_jobs = [job for job in assigned_jobs if job.get("status") != "Done"]
    overdue_jobs = [
        job for job in assigned_jobs
        if job.get("due_date") and job.get("due_date") < now and job.get("status") != "Done"
    ]

    if super_user:
        recent_activities = list(mongo.db.activity_logs.find({}).sort("created_at", -1).limit(8))
    else:
        recent_activities = list(mongo.db.activity_logs.find({
            "organization_id": {"$in": org_ids}
        }).sort("created_at", -1).limit(8)) if org_ids else []

    active_sessions = list(mongo.db.login_sessions.find({
        "user_id": user_id,
        "is_active": True
    }).sort("created_at", -1).limit(5))

    return render_template(
        "profile/profile.html",
        user=user,
        organizations=org_cards,
        assigned_jobs=assigned_jobs,
        completed_jobs=completed_jobs,
        active_jobs=active_jobs,
        overdue_jobs=overdue_jobs,
        recent_activities=recent_activities,
        active_sessions=active_sessions,
        super_user=super_user,
        now=now
    )
