from datetime import datetime
from bson import ObjectId
from extensions import mongo


def safe_object_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


def log_activity(organization_id, user_id, action, target_type, target_id=None, project_id=None):
    mongo.db.activity_logs.insert_one({
        "organization_id": ObjectId(organization_id) if organization_id else None,
        "project_id": ObjectId(project_id) if project_id else None,
        "user_id": ObjectId(user_id) if user_id else None,
        "action": action,
        "target_type": target_type,
        "target_id": ObjectId(target_id) if target_id else None,
        "created_at": datetime.utcnow()
    })


def calc_project_progress(project_id):
    project_obj_id = ObjectId(project_id)
    total = mongo.db.tasks.count_documents({"project_id": project_obj_id})

    if total == 0:
        progress = 0
    else:
        done = mongo.db.tasks.count_documents({
            "project_id": project_obj_id,
            "status": "Done"
        })
        progress = round((done / total) * 100)

    mongo.db.projects.update_one(
        {"_id": project_obj_id},
        {"$set": {"progress": progress, "updated_at": datetime.utcnow()}}
    )

    return progress


def get_user_display(user_id):
    if not user_id:
        return "Unassigned"

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return user["name"] if user else "Unknown User"
