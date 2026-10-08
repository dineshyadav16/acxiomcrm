from datetime import datetime, date, timedelta
from app.models import db, User, Customer, Lead, Opportunity, FollowUp, AuditLog

def seed_database(app=None):
    def _seed():
        db.create_all()
        
        if User.query.first():
            print("[SEED] Database already contains records. Skipping seed.")
            return

        print("[SEED] Seeding baseline demo users...")
        
        # 1. Admin User
        admin = User(username='admin', email='admin@acxiomcrm.com', role='Admin', is_active=True)
        admin.set_password('Admin@123456')
        db.session.add(admin)

        # 2. Manager User
        manager = User(username='manager', email='manager@acxiomcrm.com', role='Manager', is_active=True)
        manager.set_password('Manager@123456')
        db.session.add(manager)

        # 3. Sales Executives
        sales1 = User(username='sales1', email='sales1@acxiomcrm.com', role='Sales Executive', is_active=True)
        sales1.set_password('Sales@123456')
        db.session.add(sales1)

        sales2 = User(username='sales2', email='sales2@acxiomcrm.com', role='Sales Executive', is_active=True)
        sales2.set_password('Sales@123456')
        db.session.add(sales2)

        db.session.commit()

        print("[SEED] Seeding initial sample customers, leads, opportunities, and follow-ups...")

        # 2. Sample Customers
        c1 = Customer(
            name='Acme Global Inc',
            email='contact@acmeglobal.com',
            phone='+1-555-0199',
            address='100 Tech Blvd, Suite 400, San Jose, CA',
            status='Active',
            assigned_to_id=sales1.id,
            created_by_id=admin.id,
            notes='Key Enterprise Account'
        )
        c2 = Customer(
            name='Starlight Logistics',
            email='info@starlight.io',
            phone='+1-555-0248',
            address='55 Harbor Way, Seattle, WA',
            status='Active',
            assigned_to_id=sales2.id,
            created_by_id=manager.id,
            notes='Mid-market client interested in supply chain optimization'
        )
        db.session.add_all([c1, c2])
        db.session.commit()

        # 3. Sample Leads
        l1 = Lead(
            contact_name='Robert Chen',
            company_name='Apex Financial Services',
            email='rchen@apexfin.com',
            phone='+1-555-0312',
            source='Website',
            status='Qualified',
            priority='High',
            assigned_to_id=sales1.id,
            created_by_id=sales1.id,
            notes='Requested demo for 50 licenses.'
        )
        l2 = Lead(
            contact_name='Sarah Jenkins',
            company_name='Vanguard Retail',
            email='sjenkins@vanguardretail.com',
            phone='+1-555-0481',
            source='Referral',
            status='New',
            priority='Medium',
            assigned_to_id=sales2.id,
            created_by_id=manager.id,
            notes='Referred by Acme Global.'
        )
        db.session.add_all([l1, l2])
        db.session.commit()

        # 4. Sample Opportunities
        o1 = Opportunity(
            name='Acme Cloud Integration Deal',
            customer_id=c1.id,
            owner_id=sales1.id,
            stage='Proposal',
            amount=45000.00,
            probability=60.0,
            expected_close_date=date.today() + timedelta(days=30),
            source='Inbound',
            notes='RFP response submitted. Awaiting decision.'
        )
        o2 = Opportunity(
            name='Starlight Analytics Pilot',
            customer_id=c2.id,
            owner_id=sales2.id,
            stage='Qualification',
            amount=15000.00,
            probability=25.0,
            expected_close_date=date.today() + timedelta(days=45),
            source='Trade Show',
            notes='Initial discovery call completed.'
        )
        db.session.add_all([o1, o2])
        db.session.commit()

        # 5. Sample Follow-Ups
        f1 = FollowUp(
            target_type='Customer',
            target_id=c1.id,
            subject='Quarterly Business Review',
            type='Meeting',
            follow_up_date=datetime.utcnow() + timedelta(days=2),
            status='Planned',
            assigned_to_id=sales1.id,
            created_by_id=admin.id,
            notes='Review Q3 usage metrics and renewal terms.'
        )
        f2 = FollowUp(
            target_type='Lead',
            target_id=l1.id,
            subject='Follow up on RFP Submission',
            type='Call',
            follow_up_date=datetime.utcnow() + timedelta(days=1),
            status='Planned',
            assigned_to_id=sales1.id,
            created_by_id=sales1.id,
            notes='Call Robert to check if additional technical answers are needed.'
        )
        db.session.add_all([f1, f2])
        
        # 6. Audit Log Entry
        audit_init = AuditLog(
            user_id=admin.id,
            username=admin.username,
            action='SYSTEM_INITIALIZED',
            module='System',
            result='Success',
            metadata_json='{"info": "AcxiomCRM baseline system seeded successfully"}'
        )
        db.session.add(audit_init)
        db.session.commit()

        print("[SEED] Seeding completed successfully!")

    if app:
        with app.app_context():
            _seed()
    else:
        _seed()

if __name__ == '__main__':
    from app import create_app
    app_inst = create_app()
    seed_database(app_inst)

