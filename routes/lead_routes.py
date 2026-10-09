"""Leads page/API routes."""

from datetime import date, timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from extensions import db
from models import Customer, Lead, Opportunity
from helpers import check_record_access, log_audit, visible_leads
from validators import valid_email, valid_phone


bp = Blueprint("leads", __name__)


@bp.route("/leads")
@login_required
def leads():
    lead_list = visible_leads().order_by(Lead.created_at.desc()).all()
    return render_template("leads.html", leads=lead_list)


@bp.route("/leads/create", methods=["GET", "POST"])
@bp.route("/leads/<int:record_id>", methods=["GET", "POST"])
@login_required
def lead_form(record_id=None):
    lead = Lead.query.get_or_404(record_id) if record_id else None
    if lead:
        check_record_access(lead.assigned_to_id)

    if request.method == "POST":
        contact_name = request.form.get("contact_name", "").strip()
        company_name = request.form.get("company_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        status = request.form.get("status", "New")
        priority = request.form.get("priority", "Medium")
        notes = request.form.get("notes", "").strip()

        allowed_statuses = ["New", "Contacted", "Qualified", "Unqualified", "Converted", "Lost"]
        allowed_priorities = ["Low", "Medium", "High"]

        if not contact_name or not valid_email(email) or not valid_phone(phone):
            flash("Enter a contact name, valid email and valid phone number.", "danger")
        elif status not in allowed_statuses or priority not in allowed_priorities:
            flash("Choose a valid lead status and priority.", "danger")
        else:
            if lead is None:
                lead = Lead(
                    contact_name=contact_name,
                    company_name=company_name,
                    email=email,
                    phone=phone,
                    status=status,
                    priority=priority,
                    notes=notes,
                    assigned_to_id=current_user.id,
                    created_by_id=current_user.id,
                )
                db.session.add(lead)
                db.session.commit()
                log_audit("CREATE_LEAD", "Lead", lead.id)
                flash("Lead captured.", "success")
            else:
                lead.contact_name = contact_name
                lead.company_name = company_name
                lead.email = email
                lead.phone = phone
                lead.status = status
                lead.priority = priority
                lead.notes = notes
                db.session.commit()
                log_audit("UPDATE_LEAD", "Lead", lead.id)
                flash("Lead updated.", "success")

            return redirect(url_for("leads.leads"))

    return render_template("lead_form.html", lead=lead)


@bp.route("/leads/<int:record_id>/convert", methods=["GET", "POST"])
@login_required
def convert_lead(record_id):
    lead = Lead.query.get_or_404(record_id)
    check_record_access(lead.assigned_to_id)

    if lead.status == "Converted":
        flash("This lead has already been converted.", "warning")
        return redirect(url_for("leads.leads"))

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", "350000"))
        except ValueError:
            amount = 0

        email_exists = Customer.query.filter_by(email=lead.email).first()
        phone_exists = Customer.query.filter_by(phone=lead.phone).first()

        if amount <= 0:
            flash("Opportunity amount must be greater than zero.", "danger")
        elif email_exists or phone_exists:
            flash("A customer with this email or phone already exists.", "danger")
        else:
            customer = Customer(
                name=lead.company_name or lead.contact_name,
                email=lead.email,
                phone=lead.phone,
                status="Active",
                assigned_to_id=lead.assigned_to_id or current_user.id,
                created_by_id=current_user.id,
                notes=f"Created from lead #{lead.id}",
            )
            db.session.add(customer)
            db.session.flush()

            opportunity = Opportunity(
                name=f"{lead.company_name or lead.contact_name} CRM Project",
                customer_id=customer.id,
                owner_id=current_user.id,
                stage="Qualification",
                amount=amount,
                probability=20,
                expected_close_date=date.today() + timedelta(days=30),
            )
            db.session.add(opportunity)
            lead.status = "Converted"
            db.session.commit()

            log_audit(
                "CONVERT_LEAD", "Lead", lead.id,
                details={"customer_id": customer.id, "opportunity_id": opportunity.id},
            )
            flash("Lead converted to Customer and Opportunity.", "success")
            return redirect(url_for("customers.customers"))

    return render_template("convert_lead.html", lead=lead)
