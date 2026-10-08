from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import db, Customer, Lead, Opportunity, FollowUp, User, AuditLog

dashboard_bp = Blueprint('dashboard', __name__)

def get_date_range_filter(range_option, start_date_str=None, end_date_str=None):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
    
    if range_option == 'today':
        return today_start, now
    elif range_option == 'this_week':
        week_start = today_start - timedelta(days=today_start.weekday())
        return week_start, now
    elif range_option == 'this_month':
        month_start = datetime(now.year, now.month, 1, 0, 0, 0)
        return month_start, now
    elif range_option == 'custom' and start_date_str and end_date_str:
        try:
            s_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            e_dt = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            return s_dt, e_dt
        except ValueError:
            pass
    return None, None

@dashboard_bp.route('/')
@login_required
def index():
    range_option = request.args.get('date_range', 'all')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_dt, end_dt = get_date_range_filter(range_option, start_date_str, end_date_str)

    # Scoping queries based on user role
    customer_q = Customer.query
    lead_q = Lead.query
    opp_q = Opportunity.query
    followup_q = FollowUp.query

    if current_user.role == 'Sales Executive':
        customer_q = customer_q.filter(Customer.assigned_to_id == current_user.id)
        lead_q = lead_q.filter(Lead.assigned_to_id == current_user.id)
        opp_q = opp_q.filter(Opportunity.owner_id == current_user.id)
        followup_q = followup_q.filter(FollowUp.assigned_to_id == current_user.id)

    # Date range filters
    if start_dt and end_dt:
        customer_q = customer_q.filter(Customer.created_at.between(start_dt, end_dt))
        lead_q = lead_q.filter(Lead.created_at.between(start_dt, end_dt))
        opp_q = opp_q.filter(Opportunity.created_at.between(start_dt, end_dt))
        followup_q = followup_q.filter(FollowUp.created_at.between(start_dt, end_dt))

    # Metrics
    total_customers = customer_q.count()
    open_leads = lead_q.filter(Lead.status.in_(['New', 'Contacted', 'Qualified'])).count()
    active_opportunities = opp_q.filter(Opportunity.stage.in_(['Qualification', 'Proposal', 'Negotiation'])).count()
    pending_followups = followup_q.filter(FollowUp.status == 'Planned').count()

    # Calculate Total Pipeline & Weighted Pipeline
    active_opps = opp_q.filter(Opportunity.stage.in_(['Qualification', 'Proposal', 'Negotiation'])).all()
    total_pipeline = sum(o.amount for o in active_opps)
    weighted_pipeline = sum(o.weighted_pipeline for o in active_opps)

    # Opportunity Stage Breakdown for Charts
    opp_stages = ['Qualification', 'Proposal', 'Negotiation', 'Won', 'Lost']
    stage_counts = []
    for st in opp_stages:
        cnt = opp_q.filter(Opportunity.stage == st).count()
        stage_counts.append(cnt)

    # Lead Status Breakdown for Charts
    lead_statuses = ['New', 'Contacted', 'Qualified', 'Unqualified', 'Converted', 'Lost']
    lead_counts = []
    for st in lead_statuses:
        cnt = lead_q.filter(Lead.status == st).count()
        lead_counts.append(cnt)

    # Recent Follow-ups / Activities
    recent_followups = followup_q.order_by(FollowUp.follow_up_date.asc()).limit(5).all()
    
    # Admin Stats
    admin_stats = None
    if current_user.role == 'Admin':
        admin_stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'locked_users': User.query.filter_by(is_locked=True).count(),
            'total_audits': AuditLog.query.count()
        }

    return render_template(
        'dashboard/index.html',
        total_customers=total_customers,
        open_leads=open_leads,
        active_opportunities=active_opportunities,
        pending_followups=pending_followups,
        total_pipeline=round(total_pipeline, 2),
        weighted_pipeline=round(weighted_pipeline, 2),
        opp_stages=opp_stages,
        stage_counts=stage_counts,
        lead_statuses=lead_statuses,
        lead_counts=lead_counts,
        recent_followups=recent_followups,
        admin_stats=admin_stats,
        range_option=range_option,
        start_date=start_date_str,
        end_date=end_date_str
    )
