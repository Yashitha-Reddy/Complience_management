import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Loads variables from a .env file (in the same folder as this file) into the
# environment, if one exists. Real environment variables (e.g. set on a server)
# always take priority and are never overridden by .env.
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-in-production")

    # Example for MySQL:
    #   mysql+pymysql://user:password@localhost/compliance_db
    # Example for PostgreSQL:
    #   postgresql+psycopg2://user:password@localhost/compliance_db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(basedir, "compliance_dev.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max upload size
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"}
