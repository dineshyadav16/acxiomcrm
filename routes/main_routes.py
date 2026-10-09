"""Main page/API routes."""

from datetime import date
from flask import Blueprint, render_template
from flask_login import current_user, login_required
from models import Lead, Opportunity
from helpers import visible_customers, visible_leads, visible_opportunities, visible_followups


bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    customers = visible_customers().all()
    leads = visible_leads().all()
    opportunities = visible_opportunities().all()
    followups = visible_followups().all()

    open_leads = [lead for lead in leads if lead.status in ["New", "Contacted", "Qualified"]]
    open_opportunities = [
        item for item in opportunities
        if item.stage in ["Qualification", "Proposal", "Negotiation"]
    ]

    pipeline_value = sum(item.amount for item in open_opportunities)
    weighted_value = sum(item.weighted_pipeline for item in open_opportunities)
    planned_followups = [item for item in followups if item.status == "Planned"]

    lead_statuses = ["New", "Contacted", "Qualified", "Unqualified", "Converted", "Lost"]
    lead_counts = [sum(1 for lead in leads if lead.status == status) for status in lead_statuses]

    stages = ["Qualification", "Proposal", "Negotiation", "Won", "Lost"]
    stage_values = [
        sum(item.amount for item in opportunities if item.stage == stage)
        for stage in stages
    ]

    # Show the total value of won opportunities for the last six months.
    month_labels = []
    monthly_sales = []
    today = date.today()
    for months_back in range(5, -1, -1):
        month_number = today.month - months_back
        year_number = today.year
        while month_number <= 0:
            month_number += 12
            year_number -= 1
        label = f"{year_number}-{month_number:02d}"
        month_labels.append(label)
        monthly_sales.append(
            sum(
                item.amount for item in opportunities
                if item.stage == "Won"
                and item.created_at.year == year_number
                and item.created_at.month == month_number
            )
        )

    return render_template(
        "dashboard.html",
        customer_count=len(customers),
        open_lead_count=len(open_leads),
        opportunity_count=len(open_opportunities),
        followup_count=len(planned_followups),
        pipeline_value=pipeline_value,
        weighted_value=weighted_value,
        lead_statuses=lead_statuses,
        lead_counts=lead_counts,
        stages=stages,
        stage_values=stage_values,
        month_labels=month_labels,
        monthly_sales=monthly_sales,
    )
