"""Admin page/API routes."""

import csv
from io import StringIO
from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from extensions import db
from models import AuditLog, Lead, Opportunity, User, Customer
from helpers import log_audit, role_required
from validators import valid_email, valid_pwd


bp = Blueprint("admin", __name__)


@bp.route("/users")
@login_required
@role_required("Admin")
def users():
    user_list = User.query.order_by(User.username).all()
    return render_template("users.html", users=user_list)


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def user_create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Sales Executive")
        password_ok, password_message = valid_pwd(password)
        allowed_roles = ["Admin", "Manager", "Sales Executive"]

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if not username or not valid_email(email):
            flash("Enter a username and valid email address.", "danger")
        elif not password_ok:
            flash(password_message, "danger")
        elif existing_user:
            flash("That username or email is already registered.", "danger")
        elif role not in allowed_roles:
            flash("Choose a valid role.", "danger")
        else:
            new_user = User(username=username, email=email, role=role, is_active=True)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            log_audit("CREATE_USER", "User", new_user.id)
            flash("User account created.", "success")
            return redirect(url_for("admin.users"))

    return render_template("user_form.html")


@bp.route("/users/<int:record_id>/unlock", methods=["POST"])
@login_required
@role_required("Admin")
def user_unlock(record_id):
    user = User.query.get_or_404(record_id)
    user.is_locked = False
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
    log_audit("ADMIN_UNLOCK_USER", "User", user.id)
    flash(f"Account for {user.username} unlocked.", "success")
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------------------
# Audit logs and CSV reports
# ---------------------------------------------------------------------------


@bp.route("/audit-logs")
@login_required
@role_required("Admin", "Manager")
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template("audit_logs.html", logs=logs)


@bp.route("/reports")
@login_required
@role_required("Admin", "Manager")
def reports():
    return render_template("reports.html")


@bp.route("/reports/export/<report_type>")
@login_required
@role_required("Admin", "Manager")
def export_csv(report_type):
    output = StringIO()
    writer = csv.writer(output)

    if report_type == "customers":
        writer.writerow(["ID", "Name", "Email", "Phone", "Status"])
        for item in Customer.query.order_by(Customer.id).all():
            writer.writerow([item.id, item.name, item.email, item.phone, item.status])
    elif report_type == "leads":
        writer.writerow(["ID", "Contact", "Company", "Email", "Status", "Priority"])
        for item in Lead.query.order_by(Lead.id).all():
            writer.writerow([
                item.id, item.contact_name, item.company_name,
                item.email, item.status, item.priority,
            ])
    elif report_type == "opportunities":
        writer.writerow(["ID", "Name", "Stage", "Amount INR", "Probability", "Weighted INR"])
        for item in Opportunity.query.order_by(Opportunity.id).all():
            writer.writerow([
                item.id, item.name, item.stage, item.amount,
                item.probability, item.weighted_pipeline,
            ])
    else:
        return "Invalid report type.", 400

    log_audit("EXPORT_REPORT", "Report", details={"type": report_type})
    filename = f"{report_type}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
