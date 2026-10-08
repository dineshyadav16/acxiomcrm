from flask import Blueprint, jsonify, request
from flask_login import login_user, current_user, login_required
from app.models import db, User, Customer, Lead, Opportunity, FollowUp, AuditLog
from app.utils.validators import validate_email, validate_phone, validate_opportunity_fields
from app.utils.auth_helpers import check_account_lockout, handle_failed_login, reset_failed_logins
from app.utils.audit_logger import log_audit

api_bp = Blueprint('api', __name__)

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username_or_email = data.get('username', '').strip()
    password = data.get('password', '')

    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if user:
        is_locked, lock_msg = check_account_lockout(user)
        if is_locked:
            return jsonify({'error': 'Account Locked', 'message': lock_msg}), 403

        if not user.is_active:
            return jsonify({'error': 'Forbidden', 'message': 'Account is deactivated.'}), 403

        if user.check_password(password):
            reset_failed_logins(user)
            login_user(user)
            log_audit('API_LOGIN_SUCCESS', 'Auth', record_id=user.id, result='Success', user=user)
            return jsonify({
                'status': 'success',
                'message': 'Logged in successfully',
                'user': user.to_dict()
            }), 200
        else:
            err_msg = handle_failed_login(user)
            return jsonify({'error': 'Unauthorized', 'message': err_msg}), 401
    else:
        err_msg = handle_failed_login(None, username_attempt=username_or_email)
        return jsonify({'error': 'Unauthorized', 'message': err_msg}), 401

@api_bp.route('/customers', methods=['GET'])
@login_required
def get_customers():
    if current_user.role == 'Sales Executive':
        customers = Customer.query.filter_by(assigned_to_id=current_user.id).all()
    else:
        customers = Customer.query.all()
    return jsonify({'count': len(customers), 'customers': [c.to_dict() for c in customers]}), 200

@api_bp.route('/customers/<int:id>', methods=['GET'])
@login_required
def get_customer(id):
    c = Customer.query.get_or_404(id)
    if current_user.role == 'Sales Executive' and c.assigned_to_id != current_user.id:
        return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403
    return jsonify(c.to_dict()), 200

@api_bp.route('/customers', methods=['POST'])
@login_required
def create_customer():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    notes = data.get('notes', '').strip()

    valid_e, msg_e = validate_email(email)
    valid_p, msg_p = validate_phone(phone)

    if not name:
        return jsonify({'error': 'Bad Request', 'message': 'Name is required'}), 400
    if not valid_e:
        return jsonify({'error': 'Bad Request', 'message': msg_e}), 400
    if not valid_p:
        return jsonify({'error': 'Bad Request', 'message': msg_p}), 400

    if Customer.query.filter_by(email=email).first():
        return jsonify({'error': 'Conflict', 'message': f'Customer with email {email} already exists'}), 409

    c = Customer(
        name=name, email=email, phone=phone, address=address, notes=notes,
        assigned_to_id=current_user.id, created_by_id=current_user.id
    )
    db.session.add(c)
    db.session.commit()
    log_audit('API_CREATE_CUSTOMER', 'Customer', record_id=c.id)

    return jsonify(c.to_dict()), 201

@api_bp.route('/leads', methods=['GET'])
@login_required
def get_leads():
    if current_user.role == 'Sales Executive':
        leads = Lead.query.filter_by(assigned_to_id=current_user.id).all()
    else:
        leads = Lead.query.all()
    return jsonify({'count': len(leads), 'leads': [l.to_dict() for l in leads]}), 200

@api_bp.route('/opportunities', methods=['GET'])
@login_required
def get_opportunities():
    if current_user.role == 'Sales Executive':
        opps = Opportunity.query.filter_by(owner_id=current_user.id).all()
    else:
        opps = Opportunity.query.all()
    return jsonify({'count': len(opps), 'opportunities': [o.to_dict() for o in opps]}), 200

@api_bp.route('/followups', methods=['GET'])
@login_required
def get_followups():
    if current_user.role == 'Sales Executive':
        followups = FollowUp.query.filter_by(assigned_to_id=current_user.id).all()
    else:
        followups = FollowUp.query.all()
    return jsonify({'count': len(followups), 'followups': [f.to_dict() for f in followups]}), 200
