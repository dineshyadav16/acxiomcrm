"""Application setup: configure Flask and register each group of routes."""

import os
from flask import Flask
from extensions import csrf, db, login_manager
from models import User

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "SECRET_KEY is missing. Set it in your terminal before starting AcxiomCRM."
    )

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///acxiomcrm.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    """Load the user who is signed in."""
    return db.session.get(User, int(user_id))


# Importing the route files creates their Blueprints.
from routes.auth_routes import bp as auth_blueprint
from routes.main_routes import bp as main_blueprint
from routes.customer_routes import bp as customer_blueprint
from routes.lead_routes import bp as lead_blueprint
from routes.sales_routes import bp as sales_blueprint
from routes.admin_routes import bp as admin_blueprint
from routes.api_routes import bp as api_blueprint

app.register_blueprint(auth_blueprint)
app.register_blueprint(main_blueprint)
app.register_blueprint(customer_blueprint)
app.register_blueprint(lead_blueprint)
app.register_blueprint(sales_blueprint)
app.register_blueprint(admin_blueprint)
app.register_blueprint(api_blueprint)
