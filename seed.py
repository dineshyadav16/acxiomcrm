"""Add a small set of Indian demo records to a new database."""

from datetime import date, datetime, timedelta

from extensions import db
from models import AuditLog, Customer, FollowUp, Lead, Opportunity, User


def seed_database():
    """Create demo accounts and example CRM records only once."""
    if User.query.first():
        return

    admin = User(username="admin", email="admin@acxiomcrm.com", role="Admin")
    manager = User(username="manager", email="manager@acxiomcrm.com", role="Manager")
    sales_one = User(
        username="sales1", email="sales1@acxiomcrm.com", role="Sales Executive"
    )
    sales_two = User(
        username="sales2", email="sales2@acxiomcrm.com", role="Sales Executive"
    )

    admin.set_password("Admin@123456")
    manager.set_password("Manager@123456")
    sales_one.set_password("Sales@123456")
    sales_two.set_password("Sales@123456")
    db.session.add_all([admin, manager, sales_one, sales_two])
    db.session.commit()

    # Customers
    customer_one = Customer(
        name="ABC Technologies",
        email="contact@abctech.in",
        phone="+91 9876543210",
        address="Hyderabad, Telangana",
        assigned_to_id=sales_one.id,
        created_by_id=admin.id,
        notes="Technology services customer",
    )
    customer_two = Customer(
        name="BrightWave Systems",
        email="hello@brightwave.in",
        phone="+91 9876543211",
        address="Visakhapatnam, Andhra Pradesh",
        assigned_to_id=sales_two.id,
        created_by_id=manager.id,
    )
    customer_three = Customer(
        name="Crestview Retail",
        email="sales@crestview.in",
        phone="+91 9876543212",
        address="Vijayawada, Andhra Pradesh",
        assigned_to_id=sales_one.id,
        created_by_id=admin.id,
    )
    db.session.add_all([customer_one, customer_two, customer_three])
    db.session.commit()

    # Leads
    lead_one = Lead(
        contact_name="Ravi Kumar",
        company_name="XYZ Solutions",
        email="ravi.kumar@xyzsolutions.in",
        phone="+91 9876543220",
        source="Referral",
        status="Qualified",
        priority="High",
        assigned_to_id=sales_one.id,
        created_by_id=sales_one.id,
        notes="Interested in a CRM solution",
    )
    lead_two = Lead(
        contact_name="Priya Sharma",
        company_name="Delta Infotech",
        email="priya.sharma@deltainfotech.in",
        phone="+91 9876543221",
        source="Website",
        status="New",
        priority="Medium",
        assigned_to_id=sales_two.id,
        created_by_id=manager.id,
    )
    lead_three = Lead(
        contact_name="Arjun Reddy",
        company_name="Evergreen Traders",
        email="arjun.reddy@evergreen.in",
        phone="+91 9876543222",
        source="Event",
        status="Contacted",
        priority="Medium",
        assigned_to_id=sales_one.id,
        created_by_id=admin.id,
    )
    db.session.add_all([lead_one, lead_two, lead_three])
    db.session.commit()

    # Sales opportunities. The first one matches the assignment example.
    opportunity_one = Opportunity(
        name="XYZ CRM Project",
        customer_id=customer_one.id,
        owner_id=sales_one.id,
        stage="Proposal",
        amount=350000,
        probability=60,
        expected_close_date=date.today() + timedelta(days=30),
        source="Referral",
        notes="CRM setup and staff training",
    )
    opportunity_two = Opportunity(
        name="BrightWave Analytics",
        customer_id=customer_two.id,
        owner_id=sales_two.id,
        stage="Qualification",
        amount=175000,
        probability=25,
        expected_close_date=date.today() + timedelta(days=45),
        source="Website",
    )
    opportunity_three = Opportunity(
        name="Crestview Support Renewal",
        customer_id=customer_three.id,
        owner_id=sales_one.id,
        stage="Won",
        amount=90000,
        probability=100,
        expected_close_date=date.today() - timedelta(days=7),
        source="Existing Customer",
    )
    db.session.add_all([opportunity_one, opportunity_two, opportunity_three])
    db.session.commit()

    # Follow-up activities
    first_followup = FollowUp(
        target_type="Customer",
        target_id=customer_one.id,
        subject="Discuss CRM requirements",
        type="Meeting",
        follow_up_date=datetime.now() + timedelta(days=2),
        assigned_to_id=sales_one.id,
    )
    second_followup = FollowUp(
        target_type="Lead",
        target_id=lead_one.id,
        subject="Follow up on proposal",
        type="Call",
        follow_up_date=datetime.now() + timedelta(days=1),
        assigned_to_id=sales_one.id,
    )
    db.session.add_all([first_followup, second_followup])
    db.session.add(
        AuditLog(
            user_id=admin.id,
            username=admin.username,
            action="SYSTEM_INITIALIZED",
            module="System",
            result="Success",
        )
    )
    db.session.commit()
