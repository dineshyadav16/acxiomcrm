from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Customer, User, Opportunity, FollowUp, AuditLog
from app.utils.validators import validate_email, validate_phone
from app.utils.auth_helpers import role_required
from app.utils.audit_logger import log_audit

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/')
@login_required
def list_customers():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    query = Customer.query

    # RBAC Scoping
    if current_user.role == 'Sales Executive':
        query = query.filter(Customer.assigned_to_id == current_user.id)

    if search:
        query = query.filter(
            (Customer.name.ilike(f'%{search}%')) |
            (Customer.email.ilike(f'%{search}%')) |
            (Customer.phone.ilike(f'%{search}%'))
        )

    if status_filter:
        query = query.filter(Customer.status == status_filter)

    pagination = query.order_by(Customer.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    sales_reps = User.query.filter_by(is_active=True).all() if current_user.has_role('Admin', 'Manager') else []

    return render_template(
        'customers/list.html',
        customers=pagination.items,
        pagination=pagination,
        search=search,
        status_filter=status_filter,
        sales_reps=sales_reps
    )

@customers_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    sales_reps = User.query.filter_by(is_active=True).all() if current_user.has_role('Admin', 'Manager') else [current_user]

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('status', 'Active')
        assigned_to_id = request.form.get('assigned_to_id', type=int)
        notes = request.form.get('notes', '').strip()

        # Validation
        valid_e, msg_e = validate_email(email)
        valid_p, msg_p = validate_phone(phone)

        if not name:
            flash('Customer name is required.', 'danger')
        elif not valid_e:
            flash(msg_e, 'danger')
        elif not valid_p:
            flash(msg_p, 'danger')
        else:
            # Duplicate check
            existing_email = Customer.query.filter_by(email=email).first()
            existing_phone = Customer.query.filter_by(phone=phone).first()

            if existing_email:
                flash(f'A customer with email "{email}" already exists.', 'danger')
            elif existing_phone:
                flash(f'A customer with phone "{phone}" already exists.', 'danger')
            else:
                assigned_user_id = assigned_to_id if current_user.has_role('Admin', 'Manager') else current_user.id
                customer = Customer(
                    name=name,
                    email=email,
                    phone=phone,
                    address=address,
                    status=status,
                    assigned_to_id=assigned_user_id,
                    created_by_id=current_user.id,
                    notes=notes
                )
                db.session.add(customer)
                db.session.commit()

                log_audit('CREATE_CUSTOMER', 'Customer', record_id=customer.id, metadata={'name': name, 'email': email})
                flash(f'Customer "{name}" created successfully.', 'success')
                return redirect(url_for('customers.view', customer_id=customer.id))

    return render_template('customers/form.html', customer=None, sales_reps=sales_reps)

@customers_bp.route('/<int:customer_id>')
@login_required
def view(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Ownership Check
    if current_user.role == 'Sales Executive' and customer.assigned_to_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('customers.list_customers'))

    opportunities = Opportunity.query.filter_by(customer_id=customer.id).all()
    followups = FollowUp.query.filter_by(target_type='Customer', target_id=customer.id).order_by(FollowUp.follow_up_date.desc()).all()
    audit_history = AuditLog.query.filter_by(module='Customer', record_id=str(customer.id)).order_by(AuditLog.timestamp.desc()).all()

    return render_template(
        'customers/view.html',
        customer=customer,
        opportunities=opportunities,
        followups=followups,
        audit_history=audit_history
    )

@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    if current_user.role == 'Sales Executive' and customer.assigned_to_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('customers.list_customers'))

    sales_reps = User.query.filter_by(is_active=True).all() if current_user.has_role('Admin', 'Manager') else [current_user]

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('status', 'Active')
        assigned_to_id = request.form.get('assigned_to_id', type=int)
        notes = request.form.get('notes', '').strip()

        valid_e, msg_e = validate_email(email)
        valid_p, msg_p = validate_phone(phone)

        if not name:
            flash('Customer name is required.', 'danger')
        elif not valid_e:
            flash(msg_e, 'danger')
        elif not valid_p:
            flash(msg_p, 'danger')
        else:
            # Duplicate check ignoring current record
            existing_e = Customer.query.filter(Customer.email == email, Customer.id != customer.id).first()
            existing_p = Customer.query.filter(Customer.phone == phone, Customer.id != customer.id).first()

            if existing_e:
                flash(f'Another customer with email "{email}" already exists.', 'danger')
            elif existing_p:
                flash(f'Another customer with phone "{phone}" already exists.', 'danger')
            else:
                changes = {}
                if customer.name != name: changes['name'] = (customer.name, name)
                if customer.email != email: changes['email'] = (customer.email, email)
                if customer.phone != phone: changes['phone'] = (customer.phone, phone)
                if customer.status != status: changes['status'] = (customer.status, status)
                
                customer.name = name
                customer.email = email
                customer.phone = phone
                customer.address = address
                customer.status = status
                customer.notes = notes
                if current_user.has_role('Admin', 'Manager') and assigned_to_id:
                    customer.assigned_to_id = assigned_to_id

                db.session.commit()

                log_audit('UPDATE_CUSTOMER', 'Customer', record_id=customer.id, metadata=changes)
                flash(f'Customer "{name}" updated successfully.', 'success')
                return redirect(url_for('customers.view', customer_id=customer.id))

    return render_template('customers/form.html', customer=customer, sales_reps=sales_reps)
