from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, FollowUp, Customer, Lead, Opportunity, User
from app.utils.validators import validate_followup_date
from app.utils.audit_logger import log_audit

followups_bp = Blueprint('followups', __name__)

FOLLOWUP_TYPES = ['Call', 'Meeting', 'Email', 'Task']
FOLLOWUP_STATUSES = ['Planned', 'Completed', 'Missed', 'Cancelled']
TARGET_TYPES = ['Customer', 'Lead', 'Opportunity']

@followups_bp.route('/')
@login_required
def list_followups():
    filter_status = request.args.get('status', '')
    filter_view = request.args.get('view', 'upcoming') # upcoming, overdue, completed, all
    target_type = request.args.get('target_type', '')
    page = request.args.get('page', 1, type=int)

    query = FollowUp.query

    if current_user.role == 'Sales Executive':
        query = query.filter(FollowUp.assigned_to_id == current_user.id)

    now = datetime.utcnow()

    if filter_view == 'upcoming':
        query = query.filter(FollowUp.status == 'Planned', FollowUp.follow_up_date >= now)
    elif filter_view == 'overdue':
        query = query.filter(FollowUp.status == 'Planned', FollowUp.follow_up_date < now)
    elif filter_view == 'completed':
        query = query.filter(FollowUp.status == 'Completed')

    if filter_status:
        query = query.filter(FollowUp.status == filter_status)

    if target_type:
        query = query.filter(FollowUp.target_type == target_type)

    pagination = query.order_by(FollowUp.follow_up_date.asc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'followups/list.html',
        followups=pagination.items,
        pagination=pagination,
        filter_view=filter_view,
        filter_status=filter_status,
        target_type=target_type,
        statuses=FOLLOWUP_STATUSES,
        types=FOLLOWUP_TYPES,
        target_types=TARGET_TYPES,
        now=now
    )

@followups_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    sales_reps = User.query.filter_by(is_active=True).all() if current_user.has_role('Admin', 'Manager') else [current_user]

    # Pre-populate targets if passed via query params
    preset_target_type = request.args.get('target_type', 'Customer')
    preset_target_id = request.args.get('target_id', type=int)

    customers = Customer.query.filter_by(status='Active').all()
    leads = Lead.query.filter(Lead.status != 'Converted').all()
    opportunities = Opportunity.query.filter(Opportunity.stage.notin_(['Won', 'Lost'])).all()

    if request.method == 'POST':
        target_type = request.form.get('target_type', 'Customer')
        target_id = request.form.get('target_id', type=int)
        subject = request.form.get('subject', '').strip()
        f_type = request.form.get('type', 'Call')
        dt_str = request.form.get('follow_up_date', '').strip()
        assigned_to_id = request.form.get('assigned_to_id', type=int)
        notes = request.form.get('notes', '').strip()

        # Allow historical entry only if user is Admin/Manager and explicitly checked historical override
        allow_past = current_user.has_role('Admin', 'Manager') and (request.form.get('allow_past') == '1')
        valid_d, res_d = validate_followup_date(dt_str, allow_past=allow_past)

        if not subject:
            flash('Subject is required.', 'danger')
        elif not target_id:
            flash('Target entity selection is required.', 'danger')
        elif not valid_d:
            flash(res_d, 'danger')
        else:
            followup = FollowUp(
                target_type=target_type,
                target_id=target_id,
                subject=subject,
                type=f_type,
                follow_up_date=res_d,
                status='Planned',
                assigned_to_id=assigned_to_id if current_user.has_role('Admin', 'Manager') else current_user.id,
                created_by_id=current_user.id,
                notes=notes
            )
            db.session.add(followup)
            db.session.commit()

            log_audit('CREATE_FOLLOWUP', 'FollowUp', record_id=followup.id, metadata={'subject': subject, 'target': f"{target_type}:{target_id}"})
            flash('Follow-up scheduled successfully.', 'success')
            return redirect(url_for('followups.list_followups'))

    return render_template(
        'followups/form.html',
        followup=None,
        sales_reps=sales_reps,
        customers=customers,
        leads=leads,
        opportunities=opportunities,
        preset_target_type=preset_target_type,
        preset_target_id=preset_target_id,
        types=FOLLOWUP_TYPES,
        target_types=TARGET_TYPES
    )

@followups_bp.route('/<int:followup_id>/update-status', methods=['POST'])
@login_required
def update_status(followup_id):
    followup = FollowUp.query.get_or_404(followup_id)

    if current_user.role == 'Sales Executive' and followup.assigned_to_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('followups.list_followups'))

    new_status = request.form.get('status')
    notes = request.form.get('notes', '').strip()

    if new_status in FOLLOWUP_STATUSES:
        old_status = followup.status
        followup.status = new_status
        if notes:
            followup.notes = f"{followup.notes or ''}\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Status -> {new_status}: {notes}"
        if new_status == 'Completed':
            followup.completed_at = datetime.utcnow()

        db.session.commit()

        log_audit('UPDATE_FOLLOWUP_STATUS', 'FollowUp', record_id=followup.id, metadata={'old_status': old_status, 'new_status': new_status})
        flash(f'Follow-up status updated to "{new_status}".', 'success')
    
    return redirect(request.referrer or url_for('followups.list_followups'))
