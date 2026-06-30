# Compliance Management System

A Flask-based compliance management system with Admin and Employee dashboards.

## Workflow
- Admin adds employees and assigns compliance tasks with a due date, priority, and frequency.
- Employees see their assigned tasks on their dashboard.
- Employees upload supporting documents, which moves the task to "Submitted".
- Admin reviews the document and either **Approves** (task → Completed) or **Reverts**
  (task → Rejected, with a note) so the employee can re-upload.

## Tech Stack
- Flask + Flask-SQLAlchemy + Flask-Login
- Plain HTML/CSS/JS templates (Jinja2), no frontend framework
- MySQL or PostgreSQL (configurable), SQLite works out of the box for local testing

## Setup

1. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configure your database connection using a `.env` file (recommended):
   ```
   copy .env.example .env        # Windows
   cp .env.example .env          # macOS/Linux
   ```
   Then edit `.env` and fill in your real values:
   ```
   SECRET_KEY=some-long-random-string
   DATABASE_URL=postgresql+psycopg2://postgres:yourpassword@localhost:5432/compliance_management
   ```
   `config.py` automatically loads `.env` on startup via `python-dotenv`. The app falls back to
   a local SQLite file if `DATABASE_URL` isn't set at all, so `.env` is optional for quick local testing.

   `.env` is already excluded from git via `.gitignore` — never commit real credentials.

   Make sure the target database (e.g. `compliance_management`) already exists on your
   Postgres/MySQL server — SQLAlchemy creates tables, not the database itself.

3. Initialize the database and create the first admin account:
   ```
   python seed.py
   ```
   This prints a default admin login (`admin@company.com` / `Admin@123`) — change the password after first login (see Notes below).

4. Run the app:
   ```
   python app.py
   ```
   Visit http://127.0.0.1:5000

## Project Structure
```
compliance_system/
├── app.py                 # App factory + entry point
├── config.py               # Configuration (DB URL, upload settings)
├── extensions.py            # db, login_manager instances
├── models.py                # User, ComplianceTask, Document, ActivityLog
├── auth.py                  # Login/logout blueprint
├── admin_routes.py          # Admin: employees, tasks, review, activity log
├── employee_routes.py       # Employee: dashboard, task detail, uploads
├── decorators.py             # admin_required / employee_required
├── seed.py                  # DB init + default admin creation
├── requirements.txt
├── uploads/                 # Uploaded documents stored here
├── static/css/style.css
└── templates/
    ├── base.html
    ├── auth/login.html
    ├── admin/...
    └── employee/...
```

## Notes / Next Steps
- **Change password feature**: not yet built — currently an admin sets an employee's initial
  password, and there's no self-service "change password" page. Worth adding next.
- **File storage**: uploaded files are saved locally to `uploads/` with randomized filenames
  to avoid collisions. For production, consider moving to S3 or similar object storage.
- **Email notifications**: not included — you may want to notify employees when a task is
  assigned or reverted, and notify admins when a document is submitted.
- **Recurring tasks**: the `frequency` field (Monthly/Quarterly/Yearly) is stored but the system
  doesn't yet auto-generate the next occurrence when one is completed — that logic would need
  a scheduled job (e.g. APScheduler or a cron-triggered script).
- All sensitive actions (employee added/disabled, task created, document uploaded, task
  approved/reverted, login/logout) are written to `ActivityLog` for an audit trail.
