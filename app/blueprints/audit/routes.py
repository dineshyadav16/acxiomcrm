from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import AuditLog, User
from app.utils.auth_helpers import role_required

audit_bp = Blueprint('audit', __name__)

MODULES = ['Auth', 'Customer', 'Lead', 'Opportunity', 'FollowUp', 'User', 'System']
ACTIONS = ['LOGIN_SUCCESS', 'LOGIN_FAILURE', 'LOGOUT', 'CREATE_CUSTOMER', 'UPDATE_CUSTOMER',
           'CREATE_LEAD', 'UPDATE_LEAD', 'CONVERT_LEAD', 'CREATE_OPPORTUNITY', 'UPDATE_OPPORTUNITY',
           'CREATE_FOLLOWUP', 'UPDATE_FOLLOWUP_STATUS', 'CREATE_USER', 'UPDATE_USER', 'ADMIN_RESET_PASSWORD', 'ADMIN_UNLOCK_USER']

@audit_bp.route('/')
@login_required
@role_required('Admin', 'Manager')
def list_logs():
    module_filter = request.args.get('module', '')
    action_filter = request.args.get('action', '')
    result_filter = request.args.get('result', '')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    query = AuditLog.query

    if module_filter:
        query = query.filter(AuditLog.module == module_filter)

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    if result_filter:
        query = query.filter(AuditLog.result == result_filter)

    if search:
        query = query.filter(
            (AuditLog.username.ilike(f'%{search}%')) |
            (AuditLog.action.ilike(f'%{search}%')) |
            (AuditLog.record_id.ilike(f'%{search}%'))
        )

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)

    return render_template(
        'audit/list.html',
        logs=pagination.items,
        pagination=pagination,
        module_filter=module_filter,
        action_filter=action_filter,
        result_filter=result_filter,
        search=search,
        modules=MODULES,
        actions=ACTIONS
    )
