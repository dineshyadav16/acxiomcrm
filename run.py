from app import app, db, User
from seed import seed_database

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            seed_database(app)

    print("\n========================================================")
    print("  AcxiomCRM Running on http://127.0.0.1:5000")
    print("  Login: admin / Admin@123456")
    print("========================================================\n")
    app.run(host='127.0.0.1', port=5000, debug=True)
