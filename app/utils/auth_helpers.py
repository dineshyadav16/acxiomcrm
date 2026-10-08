from datetime import datetime, timedelta
from functools import wraps
from flask import flash, redirect, url_for, request, abort, jsonify
from flask_login import current_user
from app.models import db
from app.config import Config
from app.utils.audit_logger import log_audit

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.'}), 401
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if not current_user.has_role(*roles):
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Forbidden', 'message': 'Insufficient permissions.'}), 403
                flash('Access denied: You do not have permission to view this resource.', 'danger')
                return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_account_lockout(user):
    """
    Returns (is_locked: bool, error_message: str)
    """
    if not user:
        return False, None
    
    if user.is_locked:
        if user.locked_until and datetime.utcnow() > user.locked_until:
            # Lockout period expired - unlock automatically
            user.is_locked = False
            user.failed_login_attempts = 0
            user.locked_until = None
            db.session.commit()
            log_audit('AUTO_UNLOCK', 'Auth', record_id=user.id, metadata={'reason': 'Lockout duration expired'}, user=user)
            return False, None
        else:
            remaining = ""
            if user.locked_until:
                minutes_left = int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
                remaining = f" Please try again in {minutes_left} minute(s) or contact Administrator."
            return True, f"Account is locked due to multiple failed login attempts.{remaining}"
    return False, None

def handle_failed_login(user, username_attempt=None):
    if user:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= Config.MAX_FAILED_LOGIN_ATTEMPTS:
            user.is_locked = True
            user.locked_until = datetime.utcnow() + timedelta(minutes=Config.LOCKOUT_DURATION_MINUTES)
            log_audit('ACCOUNT_LOCKED', 'Auth', record_id=user.id, result='Failure',
                      metadata={'attempts': user.failed_login_attempts, 'locked_until': user.locked_until.strftime('%Y-%m-%d %H:%M:%S')}, user=user)
            db.session.commit()
            return f"Account has been locked due to {Config.MAX_FAILED_LOGIN_ATTEMPTS} consecutive failed attempts. Try again after {Config.LOCKOUT_DURATION_MINUTES} minutes."
        else:
            db.session.commit()
            attempts_left = Config.MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts
            log_audit('LOGIN_FAILURE', 'Auth', record_id=user.id, result='Failure',
                      metadata={'failed_attempts': user.failed_login_attempts}, user=user)
            return f"Invalid credentials. {attempts_left} attempt(s) remaining before account lockout."
    else:
        log_audit('LOGIN_FAILURE', 'Auth', result='Failure', metadata={'attempted_username': username_attempt})
        return "Invalid credentials."

def reset_failed_logins(user):
    if user and (user.failed_login_attempts > 0 or user.is_locked):
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        db.session.commit()
