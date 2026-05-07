import os
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure

load_dotenv()


def init_db():
    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        print("ERROR: MONGO_URI not found in .env")
        return

    try:
        client = MongoClient(mongo_uri)
        client.admin.command("ping")

        db = client.get_default_database()

        if db is None:
            print("ERROR: Database name not found in MongoDB URI.")
            print("Use a URI like:")
            print("mongodb+srv://user:pass@cluster.mongodb.net/team_project_manager")
            return

        print(f"Connected to MongoDB database: {db.name}")

        collections = [
            "users",
            "organizations",
            "projects",
            "tasks",
            "activity_logs",
            "login_sessions"
        ]

        existing_collections = db.list_collection_names()

        for col in collections:
            if col not in existing_collections:
                db.create_collection(col)
                print(f"Created collection: {col}")
            else:
                print(f"Collection already exists: {col}")

        # Users indexes
        db.users.create_index(
            [("email", ASCENDING)],
            unique=True,
            name="unique_user_email"
        )
        db.users.create_index(
            [("portal_role", ASCENDING)],
            name="user_portal_role_index"
        )
        db.users.create_index(
            [("is_active", ASCENDING)],
            name="user_active_index"
        )

        # Organizations indexes
        db.organizations.create_index(
            [("name", ASCENDING)],
            name="organization_name_index"
        )
        db.organizations.create_index(
            [("created_by", ASCENDING)],
            name="organization_created_by_index"
        )
        db.organizations.create_index(
            [("members.user_id", ASCENDING)],
            name="organization_members_index"
        )

        # Projects indexes
        db.projects.create_index(
            [("organization_id", ASCENDING)],
            name="project_organization_index"
        )
        db.projects.create_index(
            [("created_by", ASCENDING)],
            name="project_created_by_index"
        )
        db.projects.create_index(
            [("members", ASCENDING)],
            name="project_members_index"
        )

        # Jobs indexes. Collection stays named tasks internally for backward compatibility.
        db.tasks.create_index(
            [("project_id", ASCENDING)],
            name="task_project_index"
        )
        db.tasks.create_index(
            [("organization_id", ASCENDING)],
            name="task_organization_index"
        )
        db.tasks.create_index(
            [("assigned_to", ASCENDING)],
            name="task_assigned_to_index"
        )
        db.tasks.create_index(
            [("status", ASCENDING)],
            name="task_status_index"
        )
        db.tasks.create_index(
            [("due_date", ASCENDING)],
            name="task_due_date_index"
        )

        # Activity logs indexes
        db.activity_logs.create_index(
            [("organization_id", ASCENDING)],
            name="activity_organization_index"
        )
        db.activity_logs.create_index(
            [("created_at", DESCENDING)],
            name="activity_created_at_index"
        )

        # Login tracking indexes
        db.login_sessions.create_index(
            [("user_id", ASCENDING), ("session_token", ASCENDING)],
            name="login_session_user_token_index"
        )
        db.login_sessions.create_index(
            [("is_active", ASCENDING)],
            name="login_session_active_index"
        )
        db.login_sessions.create_index(
            [("created_at", DESCENDING)],
            name="login_session_created_at_index"
        )

        print("Indexes created successfully.")

        # Optional metadata document
        db.activity_logs.insert_one({
            "organization_id": None,
            "project_id": None,
            "user_id": None,
            "action": "Database initialized",
            "target_type": "system",
            "target_id": None,
            "created_at": datetime.utcnow()
        })

        # Backfill older users with the new portal role field.
        db.users.update_many({"portal_role": {"$exists": False}}, {"$set": {"portal_role": "User", "is_active": True}})

        print("Database initialization completed successfully.")

    except ConnectionFailure:
        print("ERROR: Could not connect to MongoDB Atlas.")
        print("Check your internet connection and MongoDB URI.")

    except OperationFailure as e:
        print("ERROR: MongoDB operation failed.")
        print(e)

    except Exception as e:
        print("Unexpected error:")
        print(e)


if __name__ == "__main__":
    init_db()