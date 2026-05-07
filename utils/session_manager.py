from datetime import datetime
from uuid import uuid4
from bson import ObjectId
from extensions import mongo


def create_login_session(user_id, user_agent=None, ip_address=None):
    """Create a server-side login session and return its token."""
    token = uuid4().hex
    now = datetime.utcnow()

    mongo.db.login_sessions.insert_one({
        "user_id": ObjectId(user_id),
        "session_token": token,
        "is_active": True,
        "user_agent": user_agent,
        "ip_address": ip_address,
        "created_at": now,
        "last_seen_at": now,
        "logged_out_at": None
    })

    return token


def is_login_session_valid(user_id, session_token):
    """Validate that the browser session still maps to an active server-side login."""
    if not user_id or not session_token:
        return False

    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        return False

    user = mongo.db.users.find_one({
        "_id": user_obj_id,
        "is_active": True
    })

    if not user:
        return False

    login_session = mongo.db.login_sessions.find_one({
        "user_id": user_obj_id,
        "session_token": session_token,
        "is_active": True
    })

    if not login_session:
        return False

    mongo.db.login_sessions.update_one(
        {"_id": login_session["_id"]},
        {"$set": {"last_seen_at": datetime.utcnow()}}
    )

    return True


def close_login_session(user_id, session_token):
    """Mark the current server-side login session as logged out."""
    if not user_id or not session_token:
        return

    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        return

    mongo.db.login_sessions.update_one(
        {
            "user_id": user_obj_id,
            "session_token": session_token
        },
        {
            "$set": {
                "is_active": False,
                "logged_out_at": datetime.utcnow()
            }
        }
    )
