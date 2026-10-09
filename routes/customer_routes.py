"""Customers page/API routes."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from extensions import db
from models import Customer, Opportunity
from helpers import check_record_access, log_audit, visible_customers
from validators import valid_email, valid_phone


bp = Blueprint("customers", __name__)


@bp.route("/customers")
@login_required
def customers():
    customer_list = visible_customers().order_by(Customer.created_at.desc()).all()
    return render_template("customers.html", customers=customer_list)


@bp.route("/customers/create", methods=["GET", "POST"])
@bp.route("/customers/<int:record_id>", methods=["GET", "POST"])
@login_required
def customer_form(record_id=None):
    customer = Customer.query.get_or_404(record_id) if record_id else None
    if customer:
        check_record_access(customer.assigned_to_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        status = request.form.get("status", "Active")
        notes = request.form.get("notes", "").strip()

        duplicate_email = Customer.query.filter(
            Customer.email == email,
            Customer.id != (customer.id if customer else 0),
        ).first()
        duplicate_phone = Customer.query.filter(
            Customer.phone == phone,
            Customer.id != (customer.id if customer else 0),
        ).first()

        if not name or not valid_email(email) or not valid_phone(phone):
            flash("Enter a name, valid email and valid phone number.", "danger")
        elif status not in ["Active", "Inactive"]:
            flash("Choose a valid customer status.", "danger")
        elif duplicate_email:
            flash("A customer with this email already exists.", "danger")
        elif duplicate_phone:
            flash("A customer with this phone number already exists.", "danger")
        else:
            if customer is None:
                customer = Customer(
                    name=name,
                    email=email,
                    phone=phone,
                    status=status,
                    notes=notes,
                    assigned_to_id=current_user.id,
                    created_by_id=current_user.id,
                )
                db.session.add(customer)
                db.session.commit()
                log_audit("CREATE_CUSTOMER", "Customer", customer.id)
                flash("Customer created.", "success")
            else:
                customer.name = name
                customer.email = email
                customer.phone = phone
                customer.status = status
                customer.notes = notes
                db.session.commit()
                log_audit("UPDATE_CUSTOMER", "Customer", customer.id)
                flash("Customer updated.", "success")

            return redirect(url_for("customers.customers"))

    return render_template("customer_form.html", customer=customer)


@bp.route("/customers/<int:record_id>/delete", methods=["POST"])
@login_required
def customer_delete(record_id):
    customer = Customer.query.get_or_404(record_id)
    check_record_access(customer.assigned_to_id)

    if Opportunity.query.filter_by(customer_id=customer.id).first():
        flash("This customer has opportunities. Remove those links before deleting it.", "warning")
    else:
        db.session.delete(customer)
        db.session.commit()
        log_audit("DELETE_CUSTOMER", "Customer", record_id)
        flash("Customer deleted.", "success")

    return redirect(url_for("customers.customers"))
