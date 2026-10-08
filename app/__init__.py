from flask import Flask, render_template
from flask_login import LoginManager
from app.config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.dashboard.routes import dashboard_bp
    from app.blueprints.customers.routes import customers_bp
    from app.blueprints.leads.routes import leads_bp
    from app.blueprints.followups.routes import followups_bp
    from app.blueprints.opportunities.routes import opportunities_bp
    from app.blueprints.users.routes import users_bp
    from app.blueprints.audit.routes import audit_bp
    from app.blueprints.reports.routes import reports_bp
    from app.blueprints.api.routes import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(leads_bp, url_prefix='/leads')
    app.register_blueprint(followups_bp, url_prefix='/followups')
    app.register_blueprint(opportunities_bp, url_prefix='/opportunities')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(audit_bp, url_prefix='/audit-logs')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # Global Template Context Processor
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.utcnow()}

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
