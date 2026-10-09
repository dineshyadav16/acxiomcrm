"""Start AcxiomCRM on the local computer."""

import os

from app import app
from extensions import db
from models import User
from seed import seed_database


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_database()

    port = int(os.environ.get("PORT", "5000"))
    print("AcxiomCRM is starting...")
    print(f"Open http://127.0.0.1:{port} in your browser.")
    print("Demo login: admin / Admin@123456")
    app.run(host="0.0.0.0", port=port, debug=False)
