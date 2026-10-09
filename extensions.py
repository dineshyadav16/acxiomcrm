"""Shared Flask extensions used by the application."""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# These objects are connected to the Flask app in app.py.
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
