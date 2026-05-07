from functools import wraps
from flask import session, redirect, url_for, make_response, abort, request
from bson import ObjectId
from bson.errors import InvalidId
from extensions import mongo
from utils.session_manager import is_login_session_valid

ORG_MANAGERS = ["Owner", "Admin", "Org Head"]
JOB_MANAGERS = ["Owner", "Admin", "Org Head", "Team Lead"]
ORG_ROLES = ["Admin", "Org Head", "Team Lead", "Member"]


def clear_dead_session():
    session.clear()


def has_valid_login():
    valid = is_login_session_valid(session.get("user_id"), session.get("login_token"))
    if not valid:
        clear_dead_session()
    return valid


def oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def no_cache_response(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return wrapper


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not has_valid_login():
            return redirect(url_for("auth.login", next=request.path))
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return wrapper


def get_current_user():
    user_id = oid(session.get("user_id"))
    if not user_id:
        return None
    return mongo.db.users.find_one({"_id": user_id})


def is_super_user(user_id=None):
    if user_id is None:
        user_id = session.get("user_id")
    user_obj_id = oid(user_id)
    if not user_obj_id:
        return False
    user = mongo.db.users.find_one({"_id": user_obj_id})
    return bool(user and user.get("portal_role") == "Super User")


def super_user_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not has_valid_login():
            return redirect(url_for("auth.login", next=request.path))
        if not is_super_user(session.get("user_id")):
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def get_org_role(org_id, user_id):
    org_obj_id = oid(org_id)
    user_obj_id = oid(user_id)
    if not org_obj_id or not user_obj_id:
        return None

    org = mongo.db.organizations.find_one({"_id": org_obj_id, "members.user_id": user_obj_id})
    if not org:
        return None

    for member in org.get("members", []):
        if str(member.get("user_id")) == str(user_obj_id):
            return member.get("role")
    return None


def can_manage_org(org_id, user_id):
    return is_super_user(user_id) or get_org_role(org_id, user_id) in ORG_MANAGERS


def can_manage_jobs(org_id, user_id):
    return is_super_user(user_id) or get_org_role(org_id, user_id) in JOB_MANAGERS


def is_project_member(project, user_id):
    if not project or not user_id:
        return False
    if can_manage_jobs(project.get("organization_id"), user_id):
        return True
    if str(project.get("created_by")) == str(user_id):
        return True
    return any(str(member_id) == str(user_id) for member_id in project.get("members", []))


def org_member_required(view):
    @wraps(view)
    def wrapper(org_id, *args, **kwargs):
        if not has_valid_login():
            return redirect(url_for("auth.login", next=request.path))
        user_id = session.get("user_id")
        if not is_super_user(user_id) and not get_org_role(org_id, user_id):
            abort(403)
        return view(org_id, *args, **kwargs)
    return wrapper


def org_admin_required(view):
    @wraps(view)
    def wrapper(org_id, *args, **kwargs):
        if not has_valid_login():
            return redirect(url_for("auth.login", next=request.path))
        user_id = session.get("user_id")
        if not can_manage_org(org_id, user_id):
            abort(403)
        return view(org_id, *args, **kwargs)
    return wrapper


def project_member_required(view):
    @wraps(view)
    def wrapper(project_id, *args, **kwargs):
        if not has_valid_login():
            return redirect(url_for("auth.login", next=request.path))
        user_id = session.get("user_id")
        project_obj_id = oid(project_id)
        if not project_obj_id:
            abort(404)
        project = mongo.db.projects.find_one({"_id": project_obj_id})
        if not project:
            abort(404)
        if not is_project_member(project, user_id):
            abort(403)
        return view(project_id, *args, **kwargs)
    return wrapper


def project_admin_required(view):
    @wraps(view)
    def wrapper(project_id, *args, **kwargs):
        if not has_valid_login():
            return redirect(url_for("auth.login", next=request.path))
        user_id = session.get("user_id")
        project_obj_id = oid(project_id)
        if not project_obj_id:
            abort(404)
        project = mongo.db.projects.find_one({"_id": project_obj_id})
        if not project:
            abort(404)
        if not can_manage_jobs(project["organization_id"], user_id):
            abort(403)
        return view(project_id, *args, **kwargs)
    return wrapper


def task_access_required(view):
    @wraps(view)
    def wrapper(task_id, *args, **kwargs):
        if not has_valid_login():
            return redirect(url_for("auth.login", next=request.path))
        user_id = session.get("user_id")
        task_obj_id = oid(task_id)
        if not task_obj_id:
            abort(404)
        task = mongo.db.tasks.find_one({"_id": task_obj_id})
        if not task:
            abort(404)
        is_assignee = str(task.get("assigned_to")) == str(user_id)
        is_manager = can_manage_jobs(task["organization_id"], user_id)
        if not is_assignee and not is_manager:
            abort(403)
        return view(task_id, *args, **kwargs)
    return wrapper
