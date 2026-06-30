import os
import uuid

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import ComplianceTask, Document, log_activity
from decorators import employee_required

employee_bp = Blueprint("employee", __name__)


@employee_bp.before_request
@login_required
@employee_required
def restrict_to_employees():
    pass


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@employee_bp.route("/dashboard")
def dashboard():
    my_tasks = ComplianceTask.query.filter_by(assigned_to=current_user.id).order_by(
        ComplianceTask.due_date.asc()
    ).all()

    counts = {
        "Pending": 0, "In Progress": 0, "Submitted": 0, "Completed": 0, "Rejected": 0
    }
    for t in my_tasks:
        counts[t.status] = counts.get(t.status, 0) + 1

    return render_template("employee/dashboard.html", tasks=my_tasks, counts=counts)


@employee_bp.route("/tasks/<int:task_id>")
def task_detail(task_id):
    task = ComplianceTask.query.get_or_404(task_id)
    if task.assigned_to != current_user.id:
        abort(403)
    documents = task.documents.order_by(Document.uploaded_at.desc()).all()
    return render_template("employee/task_detail.html", task=task, documents=documents)


@employee_bp.route("/tasks/<int:task_id>/upload", methods=["POST"])
def upload_document(task_id):
    task = ComplianceTask.query.get_or_404(task_id)
    if task.assigned_to != current_user.id:
        abort(403)

    if task.status in ("Completed",):
        flash("This task is already completed and locked.", "warning")
        return redirect(url_for("employee.task_detail", task_id=task_id))

    file = request.files.get("document")
    if not file or file.filename == "":
        flash("Please choose a file to upload.", "danger")
        return redirect(url_for("employee.task_detail", task_id=task_id))

    if not allowed_file(file.filename):
        flash("File type not allowed.", "danger")
        return redirect(url_for("employee.task_detail", task_id=task_id))

    original_name = secure_filename(file.filename)
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_name)
    file.save(upload_path)

    document = Document(
        filename=original_name,
        filepath=stored_name,
        task_id=task.id,
        uploaded_by=current_user.id
    )
    db.session.add(document)

    # Uploading a document moves the task into Submitted, awaiting admin review
    task.status = "Submitted"
    task.review_note = None

    log_activity(current_user.id, f"Uploaded document for task: {task.title}")
    db.session.commit()

    flash("Document uploaded and submitted for review.", "success")
    return redirect(url_for("employee.task_detail", task_id=task_id))


@employee_bp.route("/documents/<int:document_id>/download")
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    if document.task.assigned_to != current_user.id:
        abort(403)
    directory = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(directory, document.filepath, as_attachment=True, download_name=document.filename)
