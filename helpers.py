"""Common functions shared by the route files."""

import json
from functools import wraps
from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user
from extensions import db
from models import AuditLog, Customer, FollowUp, Lead, Opportunity


def log_audit(action, module, record_id=None, result="Success", details=None):
    """Save a short history record for an important action."""
    if current_user.is_authenticated:
        user_id = current_user.id
        username = current_user.username
    else:
        user_id = None
        username = "System"

    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        module=module,
        record_id=str(record_id) if record_id is not None else None,
        result=result,
        metadata_json=json.dumps(details) if details else None,
    )
    db.session.add(entry)
    db.session.commit()


def role_required(*allowed_roles):
    """Restrict a page to users with one of the listed roles."""
    def decorator(view_function):
        @wraps(view_function)
        def check_role(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Please log in."}), 401
                return redirect(url_for("auth.login"))

            if not current_user.has_role(*allowed_roles):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "You do not have permission."}), 403
                flash("Access denied: this page is for another role.", "danger")
                return redirect(url_for("main.dashboard"))

            return view_function(*args, **kwargs)
        return check_role
    return decorator


def can_access(assigned_user_id):
    """Managers and admins can see all records; sales sees their own."""
    if current_user.has_role("Admin", "Manager"):
        return True
    return assigned_user_id == current_user.id


def check_record_access(assigned_user_id):
    if not can_access(assigned_user_id):
        from flask import abort
        abort(403)


def visible_customers():
    query = Customer.query
    if current_user.role == "Sales Executive":
        query = query.filter_by(assigned_to_id=current_user.id)
    return query


def visible_leads():
    query = Lead.query
    if current_user.role == "Sales Executive":
        query = query.filter_by(assigned_to_id=current_user.id)
    return query


def visible_opportunities():
    query = Opportunity.query
    if current_user.role == "Sales Executive":
        query = query.filter_by(owner_id=current_user.id)
    return query


def visible_followups():
    query = FollowUp.query
    if current_user.role == "Sales Executive":
        query = query.filter_by(assigned_to_id=current_user.id)
    return query


def get_target_record(target_type, target_id):
    """Find the existing record linked to a follow-up."""
    model_by_type = {
        "Customer": Customer,
        "Lead": Lead,
        "Opportunity": Opportunity,
    }
    model = model_by_type.get(target_type)
    if model is None:
        return None
    return db.session.get(model, target_id)


def target_is_visible(target_type, record):
    if record is None:
        return False
    if target_type == "Opportunity":
        return can_access(record.owner_id)
    return can_access(record.assigned_to_id)
