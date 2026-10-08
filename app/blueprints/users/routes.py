from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, User
from app.utils.auth_helpers import role_required, reset_failed_logins
from app.utils.validators import validate_email, validate_password_strength
from app.utils.audit_logger import log_audit

users_bp = Blueprint('users', __name__)

ROLES = ['Admin', 'Manager', 'Sales Executive']

@users_bp.route('/')
@login_required
@role_required('Admin')
def list_users():
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '') # active, inactive, locked
    page = request.args.get('page', 1, type=int)

    query = User.query

    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )

    if role_filter:
        query = query.filter(User.role == role_filter)

    if status_filter == 'active':
        query = query.filter(User.is_active == True, User.is_locked == False)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    elif status_filter == 'locked':
        query = query.filter(User.is_locked == True)

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'users/list.html',
        users=pagination.items,
        pagination=pagination,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        roles=ROLES
    )

@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def create():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'Sales Executive')

        valid_e, msg_e = validate_email(email)
        valid_p, msg_p = validate_password_strength(password)

        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
        elif not valid_e:
            flash(msg_e, 'danger')
        elif not valid_p:
            flash(msg_p, 'danger')
        elif role not in ROLES:
            flash('Invalid role selected.', 'danger')
        else:
            if User.query.filter_by(username=username).first():
                flash(f'Username "{username}" is already taken.', 'danger')
            elif User.query.filter_by(email=email).first():
                flash(f'Email "{email}" is already registered.', 'danger')
            else:
                user = User(
                    username=username,
                    email=email,
                    role=role,
                    is_active=True
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()

                log_audit('CREATE_USER', 'User', record_id=user.id, metadata={'username': username, 'role': role})
                flash(f'User "{username}" created successfully with role "{role}".', 'success')
                return redirect(url_for('users.list_users'))

    return render_template('users/form.html', user=None, roles=ROLES)

@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', user.role)
        is_active = request.form.get('is_active') == '1'

        valid_e, msg_e = validate_email(email)

        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
        elif not valid_e:
            flash(msg_e, 'danger')
        else:
            existing_u = User.query.filter(User.username == username, User.id != user.id).first()
            existing_e = User.query.filter(User.email == email, User.id != user.id).first()

            if existing_u:
                flash(f'Username "{username}" is already taken.', 'danger')
            elif existing_e:
                flash(f'Email "{email}" is already registered.', 'danger')
            else:
                changes = {}
                if user.role != role: changes['role'] = (user.role, role)
                if user.is_active != is_active: changes['is_active'] = (user.is_active, is_active)

                user.username = username
                user.email = email
                user.role = role
                user.is_active = is_active

                db.session.commit()

                log_audit('UPDATE_USER', 'User', record_id=user.id, metadata=changes)
                flash(f'User "{username}" updated successfully.', 'success')
                return redirect(url_for('users.list_users'))

    return render_template('users/form.html', user=user, roles=ROLES)

@users_bp.route('/<int:user_id>/unlock', methods=['POST'])
@login_required
@role_required('Admin')
def unlock(user_id):
    user = User.query.get_or_404(user_id)
    reset_failed_logins(user)
    log_audit('ADMIN_UNLOCK_USER', 'User', record_id=user.id, metadata={'unlocked_username': user.username})
    flash(f'Account for user "{user.username}" has been unlocked.', 'success')
    return redirect(url_for('users.list_users'))

@users_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('Admin')
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '')

    valid_p, msg_p = validate_password_strength(new_password)
    if not valid_p:
        flash(msg_p, 'danger')
    else:
        user.set_password(new_password)
        reset_failed_logins(user)
        db.session.commit()
        log_audit('ADMIN_RESET_PASSWORD', 'User', record_id=user.id, metadata={'reset_username': user.username})
        flash(f'Password for user "{user.username}" has been reset successfully.', 'success')

    return redirect(url_for('users.list_users'))
