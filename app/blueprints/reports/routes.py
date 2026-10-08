import csv
from io import StringIO
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, Response, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import db, Customer, Lead, Opportunity, FollowUp, User, AuditLog
from app.utils.auth_helpers import role_required
from app.utils.audit_logger import log_audit

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
@role_required('Admin', 'Manager')
def index():
    # 1. Pipeline Breakdown
    pipeline_data = db.session.query(
        Opportunity.stage,
        func.count(Opportunity.id).label('count'),
        func.sum(Opportunity.amount).label('total_amount'),
        func.sum((Opportunity.amount * Opportunity.probability) / 100.0).label('weighted_amount')
    ).group_by(Opportunity.stage).all()

    # 2. Lead Source & Status Conversion Rate
    lead_source_data = db.session.query(
        Lead.source,
        func.count(Lead.id).label('total'),
        func.sum(db.case((Lead.status == 'Converted', 1), else_=0)).label('converted')
    ).group_by(Lead.source).all()

    # 3. Follow-up Performance
    followup_stats = db.session.query(
        FollowUp.status,
        func.count(FollowUp.id).label('count')
    ).group_by(FollowUp.status).all()

    # 4. User Activity Performance
    user_activity = db.session.query(
        User.username,
        User.role,
        func.count(Customer.id).label('customer_count')
    ).outerjoin(Customer, Customer.assigned_to_id == User.id).group_by(User.id).all()

    return render_template(
        'reports/index.html',
        pipeline_data=pipeline_data,
        lead_source_data=lead_source_data,
        followup_stats=followup_stats,
        user_activity=user_activity
    )

@reports_bp.route('/export/<report_type>')
@login_required
@role_required('Admin', 'Manager')
def export_csv(report_type):
    si = StringIO()
    cw = csv.writer(si)

    if report_type == 'customers':
        cw.writerow(['ID', 'Name', 'Email', 'Phone', 'Status', 'Assigned Sales Executive', 'Created At'])
        customers = Customer.query.all()
        for c in customers:
            cw.writerow([
                c.id, c.name, c.email, c.phone, c.status,
                c.assigned_sales_rep.username if c.assigned_sales_rep else 'Unassigned',
                c.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        filename = "customers_report.csv"

    elif report_type == 'leads':
        cw.writerow(['ID', 'Contact Name', 'Company', 'Email', 'Phone', 'Source', 'Status', 'Priority', 'Assigned Sales Executive', 'Created At'])
        leads = Lead.query.all()
        for l in leads:
            cw.writerow([
                l.id, l.contact_name, l.company_name or '', l.email, l.phone,
                l.source, l.status, l.priority,
                l.assigned_sales_rep.username if l.assigned_sales_rep else 'Unassigned',
                l.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        filename = "leads_report.csv"

    elif report_type == 'opportunities':
        cw.writerow(['ID', 'Opportunity Name', 'Customer', 'Owner', 'Stage', 'Amount ($)', 'Probability (%)', 'Weighted Pipeline ($)', 'Expected Close Date', 'Created At'])
        opps = Opportunity.query.all()
        for o in opps:
            cw.writerow([
                o.id, o.name, o.customer.name if o.customer else 'N/A',
                o.owner.username if o.owner else 'Unassigned',
                o.stage, o.amount, o.probability, round(o.weighted_pipeline, 2),
                o.expected_close_date.strftime('%Y-%m-%d'),
                o.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        filename = "opportunities_report.csv"

    elif report_type == 'followups':
        cw.writerow(['ID', 'Target Type', 'Target ID', 'Subject', 'Type', 'Follow-up Date', 'Status', 'Assigned User', 'Created At'])
        followups = FollowUp.query.all()
        for f in followups:
            cw.writerow([
                f.id, f.target_type, f.target_id, f.subject, f.type,
                f.follow_up_date.strftime('%Y-%m-%d %H:%M'), f.status,
                f.assigned_user.username if f.assigned_user else 'Unassigned',
                f.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        filename = "followups_report.csv"

    else:
        flash('Invalid report type for export.', 'danger')
        return redirect(url_for('reports.index'))

    log_audit('EXPORT_REPORT', 'Report', metadata={'report_type': report_type})

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
