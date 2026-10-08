import os
from app import create_app
from app.models import db, User

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Auto-seed if database is empty on start
        if not User.query.first():
            from seed import seed_database
            seed_database()

    print("\n========================================================")
    print("  AcxiomCRM Application Running on http://127.0.0.1:5000")
    print("  Login with: admin / Admin@123456")
    print("========================================================\n")
    app.run(host='127.0.0.1', port=5000, debug=True)
