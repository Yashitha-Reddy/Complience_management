"""
Run this once to create all tables and an initial Admin account.

Usage:
    python seed.py
"""
from app import create_app
from extensions import db
from models import User

app = create_app()

with app.app_context():
    db.create_all()

    existing_admin = User.query.filter_by(role="Admin").first()
    if existing_admin:
        print(f"Admin already exists: {existing_admin.email}")
    else:
        admin = User(
            full_name="System Admin",
            email="admin@company.com",
            department="Compliance",
            role="Admin"
        )
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.commit()
        print("Created default admin account:")
        print("  email:    admin@company.com")
        print("  password: Admin@123")
        print("Please log in and change this password immediately.")
