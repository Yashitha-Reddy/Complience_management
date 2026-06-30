from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    role = db.Column(
        db.Enum("Admin", "Employee", name="user_roles"),
        nullable=False
    )

    department = db.Column(db.String(50), nullable=False)
    is_active_flag = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Tasks assigned to this user (as an employee)
    assigned_tasks = db.relationship(
        "ComplianceTask",
        foreign_keys="ComplianceTask.assigned_to",
        back_populates="assignee",
        lazy="dynamic"
    )

    # Tasks created by this user (as an admin)
    created_tasks = db.relationship(
        "ComplianceTask",
        foreign_keys="ComplianceTask.created_by",
        back_populates="creator",
        lazy="dynamic"
    )

    documents = db.relationship("Document", back_populates="uploader", lazy="dynamic")
    activity_logs = db.relationship("ActivityLog", back_populates="user", lazy="dynamic")

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

    @property
    def is_admin(self):
        return self.role == "Admin"

    # Flask-Login uses is_active to block disabled accounts from logging in
    @property
    def is_active(self):
        return self.is_active_flag

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class ComplianceTask(db.Model):
    __tablename__ = "compliance_tasks"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)

    priority = db.Column(
        db.Enum("High", "Medium", "Low", name="priority_enum"),
        nullable=False
    )

    status = db.Column(
        db.Enum(
            "Pending",
            "In Progress",
            "Submitted",
            "Completed",
            "Rejected",
            name="status_enum"
        ),
        default="Pending",
        nullable=False
    )

    frequency = db.Column(
        db.Enum(
            "One Time",
            "Monthly",
            "Quarterly",
            "Yearly",
            name="frequency_enum"
        ),
        default="One Time",
        nullable=False
    )

    due_date = db.Column(db.Date)

    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Admin's review note when approving/rejecting a submitted document
    review_note = db.Column(db.Text)

    assignee = db.relationship(
        "User", foreign_keys=[assigned_to], back_populates="assigned_tasks"
    )
    creator = db.relationship(
        "User", foreign_keys=[created_by], back_populates="created_tasks"
    )

    documents = db.relationship(
        "Document", back_populates="task", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ComplianceTask {self.title} [{self.status}]>"


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    task_id = db.Column(db.Integer, db.ForeignKey("compliance_tasks.id"))
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    task = db.relationship("ComplianceTask", back_populates="documents")
    uploader = db.relationship("User", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.filename}>"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)

    action = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.action}>"


def log_activity(user_id, action):
    """Helper to record an activity log entry."""
    entry = ActivityLog(user_id=user_id, action=action)
    db.session.add(entry)
