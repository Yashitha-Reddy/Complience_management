from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app, abort
)
from flask_login import login_required, current_user

from extensions import db
from models import User, ComplianceTask, Document, ActivityLog, log_activity
from decorators import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
@login_required
@admin_required
def restrict_to_admins():
    """Ensures every route in this blueprint requires an authenticated admin."""
    pass


# ---------- Dashboard ----------

@admin_bp.route("/dashboard")
def dashboard():
    total_employees = User.query.filter_by(role="Employee").count()
    total_tasks = ComplianceTask.query.count()
    pending_review = ComplianceTask.query.filter_by(status="Submitted").count()
    overdue = ComplianceTask.query.filter(
        ComplianceTask.due_date < datetime.utcnow().date(),
        ComplianceTask.status.notin_(["Completed"])
    ).count()

    recent_logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        total_employees=total_employees,
        total_tasks=total_tasks,
        pending_review=pending_review,
        overdue=overdue,
        recent_logs=recent_logs
    )


# ---------- Employee management ----------

@admin_bp.route("/employees")
def employees():
    all_employees = User.query.filter_by(role="Employee").order_by(User.full_name).all()
    return render_template("admin/employees.html", employees=all_employees)


@admin_bp.route("/employees/add", methods=["GET", "POST"])
def add_employee():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()
        password = request.form.get("password", "")

        if not all([full_name, email, department, password]):
            flash("All fields are required.", "danger")
            return redirect(url_for("admin.add_employee"))

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("admin.add_employee"))

        employee = User(
            full_name=full_name,
            email=email,
            department=department,
            role="Employee"
        )
        employee.set_password(password)
        db.session.add(employee)
        db.session.flush()

        log_activity(current_user.id, f"Added employee: {employee.full_name} ({employee.email})")
        db.session.commit()

        flash(f"Employee {full_name} added successfully.", "success")
        return redirect(url_for("admin.employees"))

    return render_template("admin/add_employee.html")


@admin_bp.route("/employees/<int:user_id>/toggle-active", methods=["POST"])
def toggle_employee_active(user_id):
    employee = User.query.get_or_404(user_id)
    if employee.role != "Employee":
        abort(403)

    employee.is_active_flag = not employee.is_active_flag
    state = "enabled" if employee.is_active_flag else "disabled"
    log_activity(current_user.id, f"{state.capitalize()} employee: {employee.email}")
    db.session.commit()

    flash(f"Employee account {state}.", "info")
    return redirect(url_for("admin.employees"))


# ---------- Task management ----------

@admin_bp.route("/tasks")
def tasks():
    status_filter = request.args.get("status")
    query = ComplianceTask.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_tasks = query.order_by(ComplianceTask.due_date.asc()).all()
    return render_template("admin/tasks.html", tasks=all_tasks, status_filter=status_filter)


@admin_bp.route("/tasks/add", methods=["GET", "POST"])
def add_task():
    employees_list = User.query.filter_by(role="Employee", is_active_flag=True).order_by(User.full_name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority")
        frequency = request.form.get("frequency")
        due_date_str = request.form.get("due_date")
        assigned_to = request.form.get("assigned_to")

        if not all([title, priority, frequency, due_date_str, assigned_to]):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("admin.add_task"))

        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid due date format.", "danger")
            return redirect(url_for("admin.add_task"))

        task = ComplianceTask(
            title=title,
            description=description,
            priority=priority,
            frequency=frequency,
            due_date=due_date,
            assigned_to=int(assigned_to),
            created_by=current_user.id,
            status="Pending"
        )
        db.session.add(task)
        db.session.flush()

        log_activity(current_user.id, f"Created task: {task.title} (assigned to user #{assigned_to})")
        db.session.commit()

        flash("Compliance task created.", "success")
        return redirect(url_for("admin.tasks"))

    return render_template("admin/add_task.html", employees=employees_list)


@admin_bp.route("/tasks/<int:task_id>")
def task_detail(task_id):
    task = ComplianceTask.query.get_or_404(task_id)
    documents = task.documents.order_by(Document.uploaded_at.desc()).all()
    return render_template("admin/task_detail.html", task=task, documents=documents)


@admin_bp.route("/tasks/<int:task_id>/review", methods=["POST"])
def review_task(task_id):
    """Admin approves or rejects (reverts) a submitted task."""
    task = ComplianceTask.query.get_or_404(task_id)
    decision = request.form.get("decision")
    note = request.form.get("review_note", "").strip()

    if decision not in ("approve", "reject"):
        flash("Invalid decision.", "danger")
        return redirect(url_for("admin.task_detail", task_id=task_id))

    if task.status != "Submitted":
        flash("Only submitted tasks can be reviewed.", "warning")
        return redirect(url_for("admin.task_detail", task_id=task_id))

    task.status = "Completed" if decision == "approve" else "Rejected"
    task.review_note = note

    log_activity(
        current_user.id,
        f"{'Approved' if decision == 'approve' else 'Reverted'} task: {task.title}"
    )
    db.session.commit()

    flash(f"Task has been {'approved' if decision == 'approve' else 'sent back to the employee'}.", "success")
    return redirect(url_for("admin.task_detail", task_id=task_id))


@admin_bp.route("/documents/<int:document_id>/download")
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    directory = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(directory, document.filepath, as_attachment=True, download_name=document.filename)


# ---------- Activity log ----------

@admin_bp.route("/activity-log")
def activity_log():
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(200).all()
    return render_template("admin/activity_log.html", logs=logs)
