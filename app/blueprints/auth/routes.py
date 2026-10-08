from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
from app.utils.auth_helpers import check_account_lockout, handle_failed_login, reset_failed_logins
from app.utils.validators import validate_password_strength
from app.utils.audit_logger import log_audit

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if user:
            is_locked, lock_msg = check_account_lockout(user)
            if is_locked:
                flash(lock_msg, 'danger')
                return render_template('auth/login.html', username=username_or_email)

            if not user.is_active:
                flash('Your account has been deactivated. Please contact an Administrator.', 'danger')
                log_audit('LOGIN_DEACTIVATED', 'Auth', record_id=user.id, result='Failure', user=user)
                return render_template('auth/login.html', username=username_or_email)

            if user.check_password(password):
                reset_failed_logins(user)
                login_user(user, remember=request.form.get('remember', False))
                log_audit('LOGIN_SUCCESS', 'Auth', record_id=user.id, result='Success', user=user)
                
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('dashboard.index')
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(next_page)
            else:
                err_msg = handle_failed_login(user)
                flash(err_msg, 'danger')
        else:
            err_msg = handle_failed_login(None, username_attempt=username_or_email)
            flash(err_msg, 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_audit('LOGOUT', 'Auth', record_id=current_user.id, result='Success')
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            current_pwd = request.form.get('current_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pwd):
                flash('Current password is incorrect.', 'danger')
            elif new_pwd != confirm_pwd:
                flash('New password and confirmation do not match.', 'danger')
            else:
                is_valid, val_msg = validate_password_strength(new_pwd)
                if not is_valid:
                    flash(val_msg, 'danger')
                else:
                    current_user.set_password(new_pwd)
                    db.session.commit()
                    log_audit('PASSWORD_CHANGE', 'Auth', record_id=current_user.id, result='Success')
                    flash('Your password has been updated successfully.', 'success')

    return render_template('auth/profile.html')
