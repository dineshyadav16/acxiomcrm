from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Opportunity, Customer, User, FollowUp
from app.utils.validators import validate_opportunity_fields
from app.utils.audit_logger import log_audit

opportunities_bp = Blueprint('opportunities', __name__)

OPPORTUNITY_STAGES = ['Qualification', 'Proposal', 'Negotiation', 'Won', 'Lost']

@opportunities_bp.route('/')
@login_required
def list_opportunities():
    stage_filter = request.args.get('stage', '')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Opportunity.query

    if current_user.role == 'Sales Executive':
        query = query.filter(Opportunity.owner_id == current_user.id)

    if stage_filter:
        query = query.filter(Opportunity.stage == stage_filter)

    if search:
        query = query.filter(Opportunity.name.ilike(f'%{search}%'))

    pagination = query.order_by(Opportunity.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

    # Calculate Summary Totals
    all_active_opps = query.filter(Opportunity.stage.in_(['Qualification', 'Proposal', 'Negotiation'])).all()
    total_pipeline = sum(o.amount for o in all_active_opps)
    total_weighted = sum(o.weighted_pipeline for o in all_active_opps)

    return render_template(
        'opportunities/list.html',
        opportunities=pagination.items,
        pagination=pagination,
        stage_filter=stage_filter,
        search=search,
        stages=OPPORTUNITY_STAGES,
        total_pipeline=round(total_pipeline, 2),
        total_weighted=round(total_weighted, 2)
    )

@opportunities_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    sales_reps = User.query.filter_by(is_active=True).all() if current_user.has_role('Admin', 'Manager') else [current_user]
    customers = Customer.query.filter_by(status='Active').all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        customer_id = request.form.get('customer_id', type=int)
        owner_id = request.form.get('owner_id', type=int)
        stage = request.form.get('stage', 'Qualification')
        amount_str = request.form.get('amount', '0')
        prob_str = request.form.get('probability', '10')
        close_date_str = request.form.get('expected_close_date', '').strip()
        source = request.form.get('source', '').strip()
        notes = request.form.get('notes', '').strip()

        is_active = stage not in ['Won', 'Lost']
        valid_o, res_o = validate_opportunity_fields(amount_str, prob_str, close_date_str, is_active=is_active)

        if not name:
            flash('Opportunity name is required.', 'danger')
        elif not valid_o:
            flash(res_o, 'danger')
        else:
            amt, prob, exp_date = res_o
            opp = Opportunity(
                name=name,
                customer_id=customer_id,
                owner_id=owner_id if current_user.has_role('Admin', 'Manager') else current_user.id,
                stage=stage,
                amount=amt,
                probability=prob,
                expected_close_date=exp_date,
                source=source,
                notes=notes
            )
            db.session.add(opp)
            db.session.commit()

            log_audit('CREATE_OPPORTUNITY', 'Opportunity', record_id=opp.id, metadata={
                'name': name, 'amount': amt, 'probability': prob, 'weighted': opp.weighted_pipeline
            })
            flash(f'Opportunity "{name}" created successfully.', 'success')
            return redirect(url_for('opportunities.view', opp_id=opp.id))

    return render_template(
        'opportunities/form.html',
        opportunity=None,
        sales_reps=sales_reps,
        customers=customers,
        stages=OPPORTUNITY_STAGES
    )

@opportunities_bp.route('/<int:opp_id>')
@login_required
def view(opp_id):
    opp = Opportunity.query.get_or_404(opp_id)

    if current_user.role == 'Sales Executive' and opp.owner_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('opportunities.list_opportunities'))

    followups = FollowUp.query.filter_by(target_type='Opportunity', target_id=opp.id).order_by(FollowUp.follow_up_date.desc()).all()

    return render_template('opportunities/view.html', opportunity=opp, followups=followups, stages=OPPORTUNITY_STAGES)

@opportunities_bp.route('/<int:opp_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(opp_id):
    opp = Opportunity.query.get_or_404(opp_id)

    if current_user.role == 'Sales Executive' and opp.owner_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('opportunities.list_opportunities'))

    sales_reps = User.query.filter_by(is_active=True).all() if current_user.has_role('Admin', 'Manager') else [current_user]
    customers = Customer.query.filter_by(status='Active').all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        customer_id = request.form.get('customer_id', type=int)
        owner_id = request.form.get('owner_id', type=int)
        stage = request.form.get('stage', opp.stage)
        amount_str = request.form.get('amount', str(opp.amount))
        prob_str = request.form.get('probability', str(opp.probability))
        close_date_str = request.form.get('expected_close_date', '').strip()
        source = request.form.get('source', '').strip()
        notes = request.form.get('notes', '').strip()

        is_active = stage not in ['Won', 'Lost']
        valid_o, res_o = validate_opportunity_fields(amount_str, prob_str, close_date_str, is_active=is_active)

        if not name:
            flash('Opportunity name is required.', 'danger')
        elif not valid_o:
            flash(res_o, 'danger')
        else:
            amt, prob, exp_date = res_o
            
            changes = {}
            if opp.stage != stage: changes['stage'] = (opp.stage, stage)
            if opp.amount != amt: changes['amount'] = (opp.amount, amt)
            if opp.probability != prob: changes['probability'] = (opp.probability, prob)

            opp.name = name
            opp.customer_id = customer_id
            opp.stage = stage
            opp.amount = amt
            opp.probability = prob
            opp.expected_close_date = exp_date
            opp.source = source
            opp.notes = notes
            if current_user.has_role('Admin', 'Manager') and owner_id:
                opp.owner_id = owner_id

            db.session.commit()

            log_audit('UPDATE_OPPORTUNITY', 'Opportunity', record_id=opp.id, metadata=changes)
            flash(f'Opportunity "{name}" updated successfully.', 'success')
            return redirect(url_for('opportunities.view', opp_id=opp.id))

    return render_template(
        'opportunities/form.html',
        opportunity=opp,
        sales_reps=sales_reps,
        customers=customers,
        stages=OPPORTUNITY_STAGES
    )
