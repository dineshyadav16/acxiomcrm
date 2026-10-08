from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Lead, Customer, Opportunity, User, FollowUp
from app.utils.validators import validate_email, validate_phone, validate_lead_status_transition, validate_opportunity_fields
from app.utils.audit_logger import log_audit

leads_bp = Blueprint('leads', __name__)

LEAD_SOURCES = ['Website', 'Referral', 'Cold Call', 'Trade Show', 'Social Media', 'Other']
LEAD_STATUSES = ['New', 'Contacted', 'Qualified', 'Unqualified', 'Converted', 'Lost']
LEAD_PRIORITIES = ['Low', 'Medium', 'High']

@leads_bp.route('/')
@login_required
def list_leads():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    page = request.args.get('page', 1, type=int)

    query = Lead.query

    if current_user.role == 'Sales Executive':
        query = query.filter(Lead.assigned_to_id == current_user.id)

    if search:
        query = query.filter(
            (Lead.contact_name.ilike(f'%{search}%')) |
            (Lead.company_name.ilike(f'%{search}%')) |
            (Lead.email.ilike(f'%{search}%')) |
            (Lead.phone.ilike(f'%{search}%'))
        )

    if status_filter:
        query = query.filter(Lead.status == status_filter)

    if priority_filter:
        query = query.filter(Lead.priority == priority_filter)

    pagination = query.order_by(Lead.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'leads/list.html',
        leads=pagination.items,
        pagination=pagination,
        search=search,
        status_filter=status_filter,
        priority_filter=priority_filter,
        statuses=LEAD_STATUSES,
        priorities=LEAD_PRIORITIES
    )

@leads_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    sales_reps = User.query.filter_by(is_active=True).all() if current_user.has_role('Admin', 'Manager') else [current_user]

    if request.method == 'POST':
        contact_name = request.form.get('contact_name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        source = request.form.get('source', 'Website')
        status = request.form.get('status', 'New')
        priority = request.form.get('priority', 'Medium')
        assigned_to_id = request.form.get('assigned_to_id', type=int)
        notes = request.form.get('notes', '').strip()

        valid_e, msg_e = validate_email(email)
        valid_p, msg_p = validate_phone(phone)

        if not contact_name:
            flash('Contact name is required.', 'danger')
        elif not valid_e:
            flash(msg_e, 'danger')
        elif not valid_p:
            flash(msg_p, 'danger')
        else:
            assigned_user_id = assigned_to_id if current_user.has_role('Admin', 'Manager') else current_user.id
            lead = Lead(
                contact_name=contact_name,
                company_name=company_name,
                email=email,
                phone=phone,
                source=source,
                status=status,
                priority=priority,
                assigned_to_id=assigned_user_id,
                created_by_id=current_user.id,
                notes=notes
            )
            db.session.add(lead)
            db.session.commit()

            log_audit('CREATE_LEAD', 'Lead', record_id=lead.id, metadata={'name': contact_name, 'email': email})
            flash(f'Lead "{contact_name}" created successfully.', 'success')
            return redirect(url_for('leads.view', lead_id=lead.id))

    return render_template(
        'leads/form.html',
        lead=None,
        sales_reps=sales_reps,
        sources=LEAD_SOURCES,
        statuses=LEAD_STATUSES,
        priorities=LEAD_PRIORITIES
    )

@leads_bp.route('/<int:lead_id>')
@login_required
def view(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if current_user.role == 'Sales Executive' and lead.assigned_to_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('leads.list_leads'))

    followups = FollowUp.query.filter_by(target_type='Lead', target_id=lead.id).order_by(FollowUp.follow_up_date.desc()).all()

    return render_template('leads/view.html', lead=lead, followups=followups, statuses=LEAD_STATUSES)

@leads_bp.route('/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if current_user.role == 'Sales Executive' and lead.assigned_to_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('leads.list_leads'))

    sales_reps = User.query.filter_by(is_active=True).all() if current_user.has_role('Admin', 'Manager') else [current_user]

    if request.method == 'POST':
        contact_name = request.form.get('contact_name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        source = request.form.get('source', 'Website')
        new_status = request.form.get('status', lead.status)
        priority = request.form.get('priority', 'Medium')
        assigned_to_id = request.form.get('assigned_to_id', type=int)
        notes = request.form.get('notes', '').strip()

        valid_e, msg_e = validate_email(email)
        valid_p, msg_p = validate_phone(phone)
        valid_t, msg_t = validate_lead_status_transition(lead.status, new_status)

        if not contact_name:
            flash('Contact name is required.', 'danger')
        elif not valid_e:
            flash(msg_e, 'danger')
        elif not valid_p:
            flash(msg_p, 'danger')
        elif not valid_t:
            flash(msg_t, 'danger')
        else:
            status_changed = lead.status != new_status
            lead.contact_name = contact_name
            lead.company_name = company_name
            lead.email = email
            lead.phone = phone
            lead.source = source
            lead.status = new_status
            lead.priority = priority
            lead.notes = notes
            if current_user.has_role('Admin', 'Manager') and assigned_to_id:
                lead.assigned_to_id = assigned_to_id

            db.session.commit()

            log_audit('UPDATE_LEAD', 'Lead', record_id=lead.id, metadata={'status_changed': status_changed, 'status': new_status})
            flash(f'Lead "{contact_name}" updated successfully.', 'success')
            return redirect(url_for('leads.view', lead_id=lead.id))

    return render_template(
        'leads/form.html',
        lead=lead,
        sales_reps=sales_reps,
        sources=LEAD_SOURCES,
        statuses=LEAD_STATUSES,
        priorities=LEAD_PRIORITIES
    )

@leads_bp.route('/<int:lead_id>/convert', methods=['GET', 'POST'])
@login_required
def convert(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    if current_user.role == 'Sales Executive' and lead.assigned_to_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('leads.list_leads'))

    if lead.status == 'Converted':
        flash('This lead has already been converted into a Customer.', 'warning')
        return redirect(url_for('leads.view', lead_id=lead.id))

    if request.method == 'POST':
        cust_name = request.form.get('customer_name', lead.contact_name).strip()
        cust_email = request.form.get('customer_email', lead.email).strip()
        cust_phone = request.form.get('customer_phone', lead.phone).strip()
        address = request.form.get('address', '').strip()

        create_opp = request.form.get('create_opportunity') == 'yes'
        opp_name = request.form.get('opp_name', f"Opportunity - {cust_name}").strip()
        opp_amount = request.form.get('opp_amount', 1000.0)
        opp_prob = request.form.get('opp_probability', 20.0)
        opp_close_date = request.form.get('opp_close_date', (date.today()).strftime('%Y-%m-%d'))

        valid_e, msg_e = validate_email(cust_email)
        valid_p, msg_p = validate_phone(cust_phone)

        if not valid_e:
            flash(msg_e, 'danger')
            return render_template('leads/convert.html', lead=lead)
        if not valid_p:
            flash(msg_p, 'danger')
            return render_template('leads/convert.html', lead=lead)

        if create_opp:
            v_opp, msg_opp = validate_opportunity_fields(opp_amount, opp_prob, opp_close_date, is_active=True)
            if not v_opp:
                flash(msg_opp, 'danger')
                return render_template('leads/convert.html', lead=lead)
            amt, prob, exp_date = msg_opp

        # 1. Create or Find Customer
        customer = Customer.query.filter_by(email=cust_email).first()
        if not customer:
            customer = Customer(
                name=cust_name,
                email=cust_email,
                phone=cust_phone,
                address=address,
                status='Active',
                assigned_to_id=lead.assigned_to_id or current_user.id,
                created_by_id=current_user.id,
                notes=f"Converted from Lead #{lead.id}. {lead.notes or ''}"
            )
            db.session.add(customer)
            db.session.flush()

        # 2. Optionally Create Opportunity
        opp_obj = None
        if create_opp:
            opp_obj = Opportunity(
                name=opp_name,
                customer_id=customer.id,
                owner_id=lead.assigned_to_id or current_user.id,
                stage='Qualification',
                amount=amt,
                probability=prob,
                expected_close_date=exp_date,
                source=lead.source,
                notes=f"Created upon Lead #{lead.id} conversion."
            )
            db.session.add(opp_obj)

        # 3. Update Lead Status to Converted
        lead.status = 'Converted'
        db.session.commit()

        log_audit('CONVERT_LEAD', 'Lead', record_id=lead.id, metadata={
            'customer_id': customer.id,
            'opportunity_id': opp_obj.id if opp_obj else None
        })

        flash(f'Lead successfully converted! Created Customer record "{customer.name}".', 'success')
        return redirect(url_for('customers.view', customer_id=customer.id))

    return render_template('leads/convert.html', lead=lead)
