"""Api page/API routes."""

from datetime import date, datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user
from flask_wtf.csrf import generate_csrf
from extensions import csrf, db
from models import Customer, FollowUp, Lead, Opportunity, User
from helpers import can_access, log_audit, visible_customers, visible_followups, visible_leads, visible_opportunities
from validators import valid_email, valid_phone


bp = Blueprint("api", __name__)


@bp.route("/api/v1/auth/login", methods=["POST"])
@csrf.exempt  # The login endpoint has no session yet, so it cannot send a CSRF token.
def api_login():
    data = request.get_json(silent=True) or {}
    login_name = data.get("username", "")
    password = data.get("password", "")

    user = User.query.filter(
        (User.username == login_name) | (User.email == login_name)
    ).first()

    if user is None:
        log_audit("API_LOGIN_FAILURE", "Auth", result="Failure")
        return jsonify({"error": "Unauthorized"}), 401

    if user.is_locked:
        lock_has_ended = user.locked_until and datetime.now() >= user.locked_until
        if lock_has_ended:
            user.is_locked = False
            user.failed_attempts = 0
            user.locked_until = None
            db.session.commit()
        else:
            return jsonify({"error": "Account is locked"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is inactive"}), 401

    if not user.check_password(password):
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.is_locked = True
            user.locked_until = datetime.now() + timedelta(minutes=15)
            db.session.commit()
            log_audit("API_ACCOUNT_LOCKED", "Auth", user.id, result="Failure")
        else:
            db.session.commit()
            log_audit("API_LOGIN_FAILURE", "Auth", user.id, result="Failure")
        return jsonify({"error": "Unauthorized"}), 401

    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
    login_user(user)
    log_audit("API_LOGIN_SUCCESS", "Auth", user.id)
    return jsonify({"status": "success", "user": user.to_dict()}), 200


@bp.route("/api/v1/customers", methods=["GET", "POST"])
@login_required
def api_customers():
    if request.method == "GET":
        return jsonify([item.to_dict() for item in visible_customers().all()]), 200

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = str(data.get("phone", "")).strip()
    status = data.get("status", "Active")

    if not name or not valid_email(email) or not valid_phone(phone):
        return jsonify({"error": "Provide a name, valid email and valid phone."}), 400
    if status not in ["Active", "Inactive"]:
        return jsonify({"error": "Invalid customer status."}), 400
    if Customer.query.filter((Customer.email == email) | (Customer.phone == phone)).first():
        return jsonify({"error": "Email or phone already exists."}), 409

    customer = Customer(
        name=name,
        email=email,
        phone=phone,
        status=status,
        address=str(data.get("address", "")).strip(),
        notes=str(data.get("notes", "")).strip(),
        assigned_to_id=current_user.id,
        created_by_id=current_user.id,
    )
    db.session.add(customer)
    db.session.commit()
    log_audit("API_CREATE_CUSTOMER", "Customer", customer.id)
    return jsonify(customer.to_dict()), 201


@bp.route("/api/v1/customers/<int:record_id>", methods=["PUT", "DELETE"])
@login_required
def api_customer_detail(record_id):
    customer = Customer.query.get_or_404(record_id)
    if not can_access(customer.assigned_to_id):
        return jsonify({"error": "Forbidden"}), 403

    if request.method == "DELETE":
        if Opportunity.query.filter_by(customer_id=customer.id).first():
            return jsonify({"error": "Customer has linked opportunities."}), 409
        db.session.delete(customer)
        db.session.commit()
        log_audit("API_DELETE_CUSTOMER", "Customer", record_id)
        return jsonify({"message": "Customer deleted."}), 200

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", customer.name)).strip()
    email = str(data.get("email", customer.email)).strip().lower()
    phone = str(data.get("phone", customer.phone)).strip()
    status = data.get("status", customer.status)

    if not name or not valid_email(email) or not valid_phone(phone):
        return jsonify({"error": "Provide a name, valid email and valid phone."}), 400
    if status not in ["Active", "Inactive"]:
        return jsonify({"error": "Invalid customer status."}), 400

    duplicate = Customer.query.filter(
        Customer.id != customer.id,
        ((Customer.email == email) | (Customer.phone == phone)),
    ).first()
    if duplicate:
        return jsonify({"error": "Email or phone already exists."}), 409

    customer.name = name
    customer.email = email
    customer.phone = phone
    customer.status = status
    customer.address = str(data.get("address", customer.address or "")).strip()
    customer.notes = str(data.get("notes", customer.notes or "")).strip()
    db.session.commit()
    log_audit("API_UPDATE_CUSTOMER", "Customer", customer.id)
    return jsonify(customer.to_dict()), 200


@bp.route("/api/v1/leads", methods=["GET", "POST"])
@login_required
def api_leads():
    if request.method == "GET":
        return jsonify([item.to_dict() for item in visible_leads().all()]), 200

    data = request.get_json(silent=True) or {}
    contact_name = str(data.get("contact_name", "")).strip()
    company_name = str(data.get("company_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = str(data.get("phone", "")).strip()
    status = data.get("status", "New")
    priority = data.get("priority", "Medium")

    if not contact_name or not valid_email(email) or not valid_phone(phone):
        return jsonify({"error": "Provide a contact name, valid email and valid phone."}), 400
    if status not in ["New", "Contacted", "Qualified", "Unqualified", "Converted", "Lost"]:
        return jsonify({"error": "Invalid lead status."}), 400
    if priority not in ["Low", "Medium", "High"]:
        return jsonify({"error": "Invalid lead priority."}), 400

    lead = Lead(
        contact_name=contact_name,
        company_name=company_name,
        email=email,
        phone=phone,
        status=status,
        priority=priority,
        assigned_to_id=current_user.id,
        created_by_id=current_user.id,
        notes=str(data.get("notes", "")).strip(),
    )
    db.session.add(lead)
    db.session.commit()
    log_audit("API_CREATE_LEAD", "Lead", lead.id)
    return jsonify(lead.to_dict()), 201


@bp.route("/api/v1/opportunities", methods=["GET", "POST"])
@login_required
def api_opportunities():
    if request.method == "GET":
        return jsonify([item.to_dict() for item in visible_opportunities().all()]), 200

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    try:
        amount = float(data.get("amount", 0))
        probability = float(data.get("probability", 0))
        customer_id = int(data["customer_id"]) if data.get("customer_id") else None
    except (TypeError, ValueError):
        return jsonify({"error": "Amount, probability or customer ID is invalid."}), 400

    stage = data.get("stage", "Qualification")
    close_date_text = str(data.get("expected_close_date", ""))
    try:
        close_date = datetime.strptime(close_date_text, "%Y-%m-%d").date()
    except ValueError:
        close_date = None

    customer = Customer.query.get(customer_id) if customer_id else None
    if not name or amount <= 0 or not 0 <= probability <= 100:
        return jsonify({"error": "Name, amount > 0 and probability from 0 to 100 are required."}), 400
    if stage not in ["Qualification", "Proposal", "Negotiation", "Won", "Lost"]:
        return jsonify({"error": "Invalid opportunity stage."}), 400
    if customer_id and (not customer or not can_access(customer.assigned_to_id)):
        return jsonify({"error": "Customer not found or not accessible."}), 400
    if not close_date or (stage not in ["Won", "Lost"] and close_date < date.today()):
        return jsonify({"error": "Enter a valid close date."}), 400

    opportunity = Opportunity(
        name=name,
        customer_id=customer_id,
        owner_id=current_user.id,
        stage=stage,
        amount=amount,
        probability=probability,
        expected_close_date=close_date,
        notes=str(data.get("notes", "")).strip(),
    )
    db.session.add(opportunity)
    db.session.commit()
    log_audit("API_CREATE_OPPORTUNITY", "Opportunity", opportunity.id)
    return jsonify(opportunity.to_dict()), 201


@bp.route("/api/v1/followups", methods=["GET"])
@login_required
def api_followups():
    followup_list = visible_followups().order_by(FollowUp.follow_up_date).all()
    return jsonify([item.to_dict() for item in followup_list]), 200


@bp.route("/api/v1/csrf-token")
@login_required
def api_csrf_token():
    """Return a token for API requests that change stored data."""
    return jsonify({"csrf_token": generate_csrf()}), 200
