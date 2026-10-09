"""Database tables for AcxiomCRM.

Each class represents one type of record stored in the database.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), default="Sales Executive")
    is_active = db.Column(db.Boolean, default=True)
    is_locked = db.Column(db.Boolean, default=False)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        """Store a hash, not the plain-text password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles):
        return self.role in roles

    def to_dict(self):
        """Return safe user fields for API responses."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "is_locked": self.is_locked,
        }


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.Text)
    status = db.Column(db.String(20), default="Active")
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    assigned_user = db.relationship("User", foreign_keys=[assigned_to_id])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "assigned_to": self.assigned_user.username if self.assigned_user else None,
        }


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_name = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(120))
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    source = db.Column(db.String(50), default="Website")
    status = db.Column(db.String(30), default="New")
    priority = db.Column(db.String(20), default="Medium")
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    assigned_user = db.relationship("User", foreign_keys=[assigned_to_id])

    def to_dict(self):
        return {
            "id": self.id,
            "contact_name": self.contact_name,
            "company_name": self.company_name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "priority": self.priority,
        }


class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    stage = db.Column(db.String(30), default="Qualification")
    amount = db.Column(db.Float, default=0.0)
    probability = db.Column(db.Float, default=10.0)
    expected_close_date = db.Column(db.Date, nullable=False)
    source = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    customer = db.relationship("Customer", foreign_keys=[customer_id])
    owner = db.relationship("User", foreign_keys=[owner_id])

    @property
    def weighted_pipeline(self):
        return self.amount * self.probability / 100

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "stage": self.stage,
            "amount": self.amount,
            "probability": self.probability,
            "weighted": round(self.weighted_pipeline, 2),
        }


class FollowUp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(30), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(30), default="Call")
    follow_up_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default="Planned")
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    assigned_user = db.relationship("User", foreign_keys=[assigned_to_id])

    def to_dict(self):
        return {
            "id": self.id,
            "target": f"{self.target_type}:{self.target_id}",
            "subject": self.subject,
            "type": self.type,
            "status": self.status,
            "date": self.follow_up_date.strftime("%Y-%m-%d %H:%M"),
        }


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    username = db.Column(db.String(64))
    action = db.Column(db.String(64), nullable=False)
    module = db.Column(db.String(64), nullable=False)
    record_id = db.Column(db.String(64))
    result = db.Column(db.String(20), default="Success")
    metadata_json = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now)
