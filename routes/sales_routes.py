"""Sales page/API routes."""

from datetime import date, datetime, timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from extensions import db
from models import Customer, FollowUp, Opportunity
from helpers import check_record_access, get_target_record, log_audit, target_is_visible, visible_followups, visible_opportunities


bp = Blueprint("sales", __name__)


@bp.route("/opportunities")
@login_required
def opportunities():
    opportunity_list = visible_opportunities().order_by(Opportunity.created_at.desc()).all()
    return render_template("opportunities.html", opportunities=opportunity_list)


@bp.route("/opportunities/create", methods=["GET", "POST"])
@bp.route("/opportunities/<int:record_id>", methods=["GET", "POST"])
@login_required
def opportunity_form(record_id=None):
    opportunity = Opportunity.query.get_or_404(record_id) if record_id else None
    if opportunity:
        check_record_access(opportunity.owner_id)

    if current_user.role == "Sales Executive":
        customer_list = Customer.query.filter_by(
            status="Active", assigned_to_id=current_user.id
        ).all()
    else:
        customer_list = Customer.query.filter_by(status="Active").all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        customer_id = request.form.get("customer_id", type=int)
        stage = request.form.get("stage", "Qualification")

        try:
            amount = float(request.form.get("amount", "0"))
            probability = float(request.form.get("probability", "0"))
        except ValueError:
            amount = 0
            probability = -1

        close_date_text = request.form.get("expected_close_date", "")
        try:
            close_date = datetime.strptime(close_date_text, "%Y-%m-%d").date()
        except ValueError:
            close_date = None

        valid_stages = ["Qualification", "Proposal", "Negotiation", "Won", "Lost"]
        selected_customer = Customer.query.get(customer_id) if customer_id else None

        if not name or amount <= 0 or not 0 <= probability <= 100:
            flash("Enter a name, amount greater than zero and probability from 0 to 100.", "danger")
        elif stage not in valid_stages:
            flash("Choose a valid opportunity stage.", "danger")
        elif customer_id and (not selected_customer or selected_customer not in customer_list):
            flash("Choose a customer you are allowed to access.", "danger")
        elif not close_date or (stage not in ["Won", "Lost"] and close_date < date.today()):
            flash("Enter a valid close date. Active opportunities need a future date.", "danger")
        else:
            if opportunity is None:
                opportunity = Opportunity(
                    name=name,
                    customer_id=customer_id,
                    owner_id=current_user.id,
                    stage=stage,
                    amount=amount,
                    probability=probability,
                    expected_close_date=close_date,
                )
                db.session.add(opportunity)
                db.session.commit()
                log_audit("CREATE_OPPORTUNITY", "Opportunity", opportunity.id)
                flash("Opportunity created.", "success")
            else:
                opportunity.name = name
                opportunity.customer_id = customer_id
                opportunity.stage = stage
                opportunity.amount = amount
                opportunity.probability = probability
                opportunity.expected_close_date = close_date
                db.session.commit()
                log_audit("UPDATE_OPPORTUNITY", "Opportunity", opportunity.id)
                flash("Opportunity updated.", "success")

            return redirect(url_for("sales.opportunities"))

    return render_template(
        "opportunity_form.html", opportunity=opportunity, customers=customer_list
    )


# ---------------------------------------------------------------------------
# Follow-up activities
# ---------------------------------------------------------------------------


@bp.route("/followups")
@login_required
def followups():
    followup_list = visible_followups().order_by(FollowUp.follow_up_date.asc()).all()
    return render_template("followups.html", followups=followup_list)


@bp.route("/followups/create", methods=["GET", "POST"])
@login_required
def followup_create():
    if request.method == "POST":
        target_type = request.form.get("target_type", "Customer")
        target_id = request.form.get("target_id", type=int)
        subject = request.form.get("subject", "").strip()
        activity_type = request.form.get("type", "Call")
        date_text = request.form.get("follow_up_date", "")

        try:
            followup_date = datetime.strptime(date_text, "%Y-%m-%dT%H:%M")
        except ValueError:
            followup_date = None

        target = get_target_record(target_type, target_id) if target_id else None
        allowed_types = ["Call", "Meeting", "Email", "Task"]

        if not subject or not followup_date or target is None:
            flash("Enter a subject, date and existing target record.", "danger")
        elif not target_is_visible(target_type, target):
            flash("You cannot schedule an activity for that record.", "danger")
        elif activity_type not in allowed_types:
            flash("Choose a valid activity type.", "danger")
        elif followup_date < datetime.now() and not current_user.has_role("Admin", "Manager"):
            flash("Choose a future date and time.", "danger")
        else:
            followup = FollowUp(
                target_type=target_type,
                target_id=target_id,
                subject=subject,
                type=activity_type,
                follow_up_date=followup_date,
                status="Planned",
                assigned_to_id=current_user.id,
            )
            db.session.add(followup)
            db.session.commit()
            log_audit("CREATE_FOLLOWUP", "FollowUp", followup.id)
            flash("Follow-up scheduled.", "success")
            return redirect(url_for("sales.followups"))

    return render_template("followup_form.html")


@bp.route("/followups/<int:record_id>/complete", methods=["POST"])
@login_required
def followup_complete(record_id):
    followup = FollowUp.query.get_or_404(record_id)
    check_record_access(followup.assigned_to_id)

    if followup.status == "Planned":
        followup.status = "Completed"
        db.session.commit()
        log_audit("COMPLETE_FOLLOWUP", "FollowUp", followup.id)
        flash("Follow-up marked as completed.", "success")
    else:
        flash("This follow-up has already been updated.", "warning")

    return redirect(url_for("sales.followups"))
