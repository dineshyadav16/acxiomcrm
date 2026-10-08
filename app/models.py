from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='Sales Executive') # Roles: Admin, Manager, Sales Executive
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_customers = db.relationship('Customer', foreign_keys='Customer.assigned_to_id', backref='assigned_sales_rep', lazy='dynamic')
    assigned_leads = db.relationship('Lead', foreign_keys='Lead.assigned_to_id', backref='assigned_sales_rep', lazy='dynamic')
    owned_opportunities = db.relationship('Opportunity', foreign_keys='Opportunity.owner_id', backref='owner', lazy='dynamic')
    assigned_followups = db.relationship('FollowUp', foreign_keys='FollowUp.assigned_to_id', backref='assigned_user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles):
        return self.role in roles

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'is_locked': self.is_locked,
            'failed_login_attempts': self.failed_login_attempts,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=False, index=True)
    address = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False) # Active, Inactive
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    opportunities = db.relationship('Opportunity', backref='customer', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'status': self.status,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_sales_rep.username if self.assigned_sales_rep else None,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class Lead(db.Model):
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    contact_name = db.Column(db.String(120), nullable=False, index=True)
    company_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    source = db.Column(db.String(50), nullable=False, default='Website')
    status = db.Column(db.String(30), nullable=False, default='New') # New, Contacted, Qualified, Unqualified, Converted, Lost
    priority = db.Column(db.String(20), nullable=False, default='Medium') # Low, Medium, High
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'contact_name': self.contact_name,
            'company_name': self.company_name,
            'email': self.email,
            'phone': self.phone,
            'source': self.source,
            'status': self.status,
            'priority': self.priority,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_sales_rep.username if self.assigned_sales_rep else None,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class Opportunity(db.Model):
    __tablename__ = 'opportunities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stage = db.Column(db.String(30), nullable=False, default='Qualification') # Qualification, Proposal, Negotiation, Won, Lost
    amount = db.Column(db.Float, nullable=False, default=0.0)
    probability = db.Column(db.Float, nullable=False, default=10.0) # 0 to 100
    expected_close_date = db.Column(db.Date, nullable=False)
    source = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def weighted_pipeline(self):
        return (self.amount * self.probability) / 100.0

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'owner_id': self.owner_id,
            'owner_name': self.owner.username if self.owner else None,
            'stage': self.stage,
            'amount': self.amount,
            'probability': self.probability,
            'weighted_pipeline': round(self.weighted_pipeline, 2),
            'expected_close_date': self.expected_close_date.strftime('%Y-%m-%d') if self.expected_close_date else None,
            'source': self.source,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class FollowUp(db.Model):
    __tablename__ = 'followups'

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(30), nullable=False) # Customer, Lead, Opportunity
    target_id = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(30), nullable=False, default='Call') # Call, Meeting, Email, Task
    follow_up_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Planned') # Planned, Completed, Missed, Cancelled
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'subject': self.subject,
            'type': self.type,
            'follow_up_date': self.follow_up_date.strftime('%Y-%m-%d %H:%M'),
            'status': self.status,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_user.username if self.assigned_user else None,
            'notes': self.notes,
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M') if self.completed_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(64), nullable=False) # e.g. LOGIN_SUCCESS, LOGIN_FAILURE, CREATE, UPDATE, DELETE, CONVERT, ROLE_CHANGE
    module = db.Column(db.String(64), nullable=False) # Auth, Customer, Lead, Opportunity, FollowUp, User, System
    record_id = db.Column(db.String(64), nullable=True)
    result = db.Column(db.String(20), nullable=False, default='Success') # Success, Failure
    metadata_json = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username or (self.user.username if self.user else 'System/Anonymous'),
            'action': self.action,
            'module': self.module,
            'record_id': self.record_id,
            'result': self.result,
            'metadata': self.metadata_json,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None
        }
