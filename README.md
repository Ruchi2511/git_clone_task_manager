# ProjectHub - Organization Project and Job Management System

ProjectHub is a GitHub-inspired project management web application designed for organizations that need to manage teams, projects, assigned jobs, deadlines, progress, and access control from a single portal.

The system allows a Super User to manage the portal, create users, organize members into organizations, assign roles, create projects, assign jobs, and monitor progress through dashboards and activity logs.

---

## Overview

ProjectHub is a full-stack Flask and MongoDB Atlas application built for team-based project management. It supports organization-level access, role-based permissions, job assignment, dashboard analytics, profile management, and secure login-session tracking.

The application follows a structured workflow:

```text
Super User creates portal users
        ↓
Users are added to organizations
        ↓
Organization roles are assigned
        ↓
Projects are created inside organizations
        ↓
Jobs are created inside projects
        ↓
Jobs are assigned to members
        ↓
Members update job status
        ↓
Dashboards and activity logs track progress
```
## Live Deployment Link

gitclonetaskmanager-production.up.railway.app
---

## Key Features

### Authentication and Security

- Secure login and logout
- Password hashing using Flask-Bcrypt
- Session-based authentication
- Server-side login session tracking
- Protected route validation
- Browser back/forward cache protection after logout
- No-cache headers for protected pages
- Active/inactive user account handling

### Super User Portal

- Create portal users
- Manage all users
- Activate or deactivate users
- View user roles and account status
- Add users to organizations
- Access organization-level management tools

### Organization Management

- Create organizations
- View organization details
- Add members to organizations
- Remove members from organizations
- Update member roles
- Configure organization details
- View organization projects and activity

### Role-Based Access Control

The system uses a layered role model:

| Role | Main Permissions |
|---|---|
| Super User | Full portal access, user creation, organization access, system-level control |
| Admin | Organization and project management access |
| Org Head | Organization-level management access |
| Team Lead | Project and job management access |
| Member | View and update assigned jobs |

### Project Management

- Create projects inside organizations
- View all accessible projects
- Edit project details
- Add or remove project members
- Archive projects
- Track project progress
- View project-specific jobs

### Job Management

The user-facing system uses the word **Job** instead of **Task**.

Jobs support:

- Job title
- Description
- Due date
- Priority
- Status
- Assigned user
- Comments
- Project linkage
- Organization linkage
- Activity tracking

Job statuses:

```text
To Do
In Progress
Review
Done
```

Job priorities:

```text
Low
Medium
High
Critical
```

### Dashboard and Analytics

- Total jobs
- Completed jobs
- In-progress jobs
- Overdue jobs
- Assigned jobs
- Organization list
- Project list
- Recent activity
- Dashboard statistics API

### Profile Page

- User account details
- Portal role
- Active account status
- Organization count
- Job summary
- Assigned jobs list
- Recent activity
- Logout button

### UI and Styling

- Professional web dashboard layout
- Sidebar-based navigation
- Responsive pages
- Card-based sections
- Light pink/red themed interface depending on current CSS version
- Status and priority badges
- Dashboard and project views

---

## Tech Stack

### Frontend

- HTML
- CSS
- JavaScript
- Jinja2 templates

### Backend

- Python
- Flask
- Flask-PyMongo
- Flask-Bcrypt
- Flask-CORS
- Gunicorn for production

### Database

- MongoDB Atlas
- PyMongo

### Deployment

- Railway
- MongoDB Atlas
- Gunicorn WSGI server

---

## Project Structure

```text
git_clone_task_manager/
│
├── app.py
├── config.py
├── extensions.py
├── requirements.txt
├── .env.example
├── .gitignore
│
├── routes/
│   ├── auth_routes.py
│   ├── dashboard_routes.py
│   ├── organization_routes.py
│   ├── portal_routes.py
│   ├── profile_routes.py
│   ├── project_routes.py
│   └── task_routes.py
│
├── scripts/
│   ├── init_db.py
│   └── create_super_user.py
│
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── 403.html
│   ├── 404.html
│   │
│   ├── auth/
│   │   ├── login.html
│   │   └── signup.html
│   │
│   ├── dashboard/
│   │   └── dashboard.html
│   │
│   ├── organizations/
│   │   ├── create_org.html
│   │   ├── org_detail.html
│   │   └── org_config.html
│   │
│   ├── portal/
│   │   ├── users.html
│   │   └── create_user.html
│   │
│   ├── profile/
│   │   └── profile.html
│   │
│   ├── projects/
│   │   ├── project_list.html
│   │   ├── create_project.html
│   │   ├── edit_project.html
│   │   └── project_detail.html
│   │
│   └── tasks/
│       ├── create_task.html
│       ├── edit_task.html
│       └── task_detail.html
│
├── static/
│   ├── css/
│   │   ├── base.css
│   │   └── auth.css
│   │
│   └── js/
│       └── main.js
│
└── utils/
    ├── decorators.py
    ├── helpers.py
    ├── session_manager.py
    └── validators.py
```

---

## Database Collections

The MongoDB database uses the following collections:

```text
users
organizations
projects
tasks
activity_logs
login_sessions
```

Note: The internal collection name for jobs is still `tasks` for backward compatibility, but the user interface uses the word **Jobs**.

---

## Environment Variables

Create a `.env` file in the project root.

```env
MONGO_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/team_project_manager?retryWrites=true&w=majority
SECRET_KEY=replace-this-with-a-long-secret-key
FLASK_ENV=development
```

Do not upload `.env` to GitHub.

Use `.env.example` as the safe reference file.

---

## Local Setup

### 1. Clone or open the project

```bash
git clone <your-repository-url>
cd git_clone_task_manager
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env`

Add your MongoDB Atlas URI and Flask secret key.

```env
MONGO_URI=your-real-mongodb-atlas-uri
SECRET_KEY=your-secret-key
FLASK_ENV=development
```

### 5. Initialize MongoDB collections and indexes

```bash
python scripts/init_db.py
```

### 6. Create the first Super User

```bash
python scripts/create_super_user.py
```

### 7. Run the application

```bash
python app.py
```

Open the app at:

```text
http://127.0.0.1:5000
```

---

## First-Time Usage Flow

1. Run database initialization.
2. Create the first Super User using `scripts/create_super_user.py`.
3. Log in with the Super User account.
4. Go to the portal user management page.
5. Create users for the organization.
6. Create or open an organization.
7. Add users to the organization and assign roles.
8. Create projects under the organization.
9. Add project members.
10. Create and assign jobs.
11. Track progress from dashboards and activity logs.

---

## Important Routes

### Public/Auth Routes

```text
/                       Landing page
/signup                 First Super User signup flow
/login                  Login page
/logout                 Logout route
/auth/session-check     Session validation endpoint
```

### Dashboard and Profile

```text
/dashboard              Main dashboard
/profile                User profile and logout page
/api/dashboard/stats    Dashboard statistics API
```

### Portal Routes

```text
/portal/users                       View portal users
/portal/users/create                Create portal user
/portal/users/<user_id>/toggle      Activate/deactivate user
/portal/orgs/<org_id>/members/add   Add user to organization
```

### Organization Routes

```text
/organizations/create                       Create organization
/organizations/<org_id>                     Organization detail
/organizations/<org_id>/config              Organization config
/organizations/<org_id>/members/add         Add organization member
/organizations/<org_id>/members/update-role Update member role
/organizations/<org_id>/members/remove      Remove member
```

### Project Routes

```text
/projects                                      Project list
/organizations/<org_id>/projects/create        Create project
/projects/<project_id>                         Project detail
/projects/<project_id>/edit                    Edit project
/projects/<project_id>/members/add             Add project member
/projects/<project_id>/members/remove          Remove project member
/projects/<project_id>/archive                 Archive project
```

### Job Routes

```text
/projects/<project_id>/tasks/create     Create job
/tasks/<task_id>                         Job detail
/tasks/<task_id>/edit                    Edit job
/tasks/<task_id>/status                  Update job status
/tasks/<task_id>/comment                 Add job comment
/tasks/<task_id>/delete                  Delete job
```

---

## Railway Deployment

### 1. Prepare `app.py`

The bottom of `app.py` should contain:

```python
app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
```

### 2. Add a `Procfile`

Create a file named `Procfile` in the project root:

```text
web: gunicorn app:app
```

### 3. Add Railway variables

In Railway, add these environment variables:

```env
MONGO_URI=your-real-mongodb-atlas-uri
SECRET_KEY=your-long-secret-key
FLASK_ENV=production
```

### 4. MongoDB Atlas network access

For quick deployment/testing, add this to MongoDB Atlas Network Access:

```text
0.0.0.0/0
```

For stricter production security, use a static outbound IP if your deployment platform provides one.

### 5. Deploy

Push the project to GitHub and connect the repository to Railway.

Railway start command:

```bash
gunicorn app:app
```

---

## Common Deployment Errors

### Error: `ModuleNotFoundError: No module named 'main'`

Cause: Railway/Gunicorn is trying to run `main:app`, but the project file is `app.py`.

Fix:

```bash
gunicorn app:app
```

### Error: `The DNS query name does not exist: _mongodb._tcp.cluster.mongodb.net`

Cause: The MongoDB URI still contains a placeholder host such as `cluster.mongodb.net`.

Fix: Copy the real MongoDB Atlas connection string. It should look like:

```env
mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/team_project_manager?retryWrites=true&w=majority
```

---

## Security Notes

- Never commit `.env` to GitHub.
- Use strong MongoDB Atlas credentials.
- Use a long random `SECRET_KEY` in production.
- Use HTTPS in production.
- Keep `SESSION_COOKIE_SECURE=True` for production.
- Avoid exposing MongoDB Atlas to all IPs for real production systems unless necessary.

---

## Future Improvements

Possible future enhancements:

- Email invitations for organization members
- File attachments for jobs
- Job labels and milestones
- Notification system
- Calendar view for deadlines
- Drag-and-drop Kanban board
- User profile image upload
- Audit log export
- Advanced admin analytics
- Team workload balancing

---

## Project Summary

ProjectHub is a full-stack organization-based project and job management system built using Flask, MongoDB Atlas, HTML, CSS, and JavaScript. It provides a secure Super User portal, organization management, project management, job assignment, role-based access, dashboards, activity tracking, and production-ready deployment support.
