"""Auth page/API routes."""

from datetime import datetime, timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from extensions import db
from models import User
from helpers import log_audit


bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        login_name = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == login_name) | (User.email == login_name)
        ).first()

        if user is None:
            log_audit("LOGIN_FAILURE", "Auth", result="Failure")
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

        # Remove the lock when its 15-minute period has ended.
        if user.is_locked:
            if user.locked_until and datetime.now() >= user.locked_until:
                user.is_locked = False
                user.failed_attempts = 0
                user.locked_until = None
                db.session.commit()
            else:
                flash("Account locked after 5 failed attempts.", "danger")
                return render_template("login.html")

        if not user.is_active:
            flash("This account has been deactivated.", "danger")
            return render_template("login.html")

        if user.check_password(password):
            user.failed_attempts = 0
            user.locked_until = None
            db.session.commit()
            login_user(user)
            log_audit("LOGIN_SUCCESS", "Auth", record_id=user.id)
            return redirect(url_for("main.dashboard"))

        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.is_locked = True
            user.locked_until = datetime.now() + timedelta(minutes=15)
            flash("Account locked after 5 failed attempts.", "danger")
            log_audit("ACCOUNT_LOCKED", "Auth", record_id=user.id, result="Failure")
        else:
            remaining = 5 - user.failed_attempts
            flash(f"Invalid credentials. {remaining} attempts left.", "danger")
            db.session.commit()
            log_audit("LOGIN_FAILURE", "Auth", record_id=user.id, result="Failure")

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_audit("LOGOUT", "Auth", record_id=current_user.id)
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))
