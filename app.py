import os, re, json, csv
from io import StringIO
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("Set the SECRET_KEY environment variable before starting the app.")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///acxiomcrm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), default='Sales Executive') # Admin, Manager, Sales Executive
    is_active = db.Column(db.Boolean, default=True)
    is_locked = db.Column(db.Boolean, default=False)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)
    def has_role(self, *roles): return self.role in roles
    def to_dict(self): return {'id': self.id, 'username': self.username, 'email': self.email, 'role': self.role, 'is_active': self.is_active, 'is_locked': self.is_locked}

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.Text)
    status = db.Column(db.String(20), default='Active') # Active, Inactive
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_user = db.relationship('User', foreign_keys=[assigned_to_id])
    def to_dict(self): return {'id': self.id, 'name': self.name, 'email': self.email, 'phone': self.phone, 'status': self.status, 'assigned_to': self.assigned_user.username if self.assigned_user else None}

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_name = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(120))
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    source = db.Column(db.String(50), default='Website')
    status = db.Column(db.String(30), default='New') # New, Contacted, Qualified, Unqualified, Converted, Lost
    priority = db.Column(db.String(20), default='Medium') # Low, Medium, High
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_user = db.relationship('User', foreign_keys=[assigned_to_id])
    def to_dict(self): return {'id': self.id, 'contact_name': self.contact_name, 'company_name': self.company_name, 'email': self.email, 'phone': self.phone, 'status': self.status, 'priority': self.priority}

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    stage = db.Column(db.String(30), default='Qualification') # Qualification, Proposal, Negotiation, Won, Lost
    amount = db.Column(db.Float, default=0.0)
    probability = db.Column(db.Float, default=10.0)
    expected_close_date = db.Column(db.Date, nullable=False)
    source = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('Customer', foreign_keys=[customer_id])
    owner = db.relationship('User', foreign_keys=[owner_id])
    @property
    def weighted_pipeline(self): return (self.amount * self.probability) / 100.0
    def to_dict(self): return {'id': self.id, 'name': self.name, 'stage': self.stage, 'amount': self.amount, 'probability': self.probability, 'weighted': round(self.weighted_pipeline, 2)}

class FollowUp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(30), nullable=False) # Customer, Lead, Opportunity
    target_id = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(30), default='Call') # Call, Meeting, Email, Task
    follow_up_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default='Planned') # Planned, Completed, Missed, Cancelled
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_user = db.relationship('User', foreign_keys=[assigned_to_id])
    def to_dict(self): return {'id': self.id, 'target': f"{self.target_type}:{self.target_id}", 'subject': self.subject, 'type': self.type, 'status': self.status, 'date': self.follow_up_date.strftime('%Y-%m-%d %H:%M')}

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(64))
    action = db.Column(db.String(64), nullable=False)
    module = db.Column(db.String(64), nullable=False)
    record_id = db.Column(db.String(64))
    result = db.Column(db.String(20), default='Success')
    metadata_json = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

def log_audit(action, module, record_id=None, result='Success', metadata=None, user=None):
    try:
        u = user or (current_user if current_user.is_authenticated else None)
        entry = AuditLog(user_id=u.id if u else None, username=u.username if u else 'System', action=action, module=module, record_id=str(record_id) if record_id else None, result=result, metadata_json=json.dumps(metadata) if metadata else None)
        db.session.add(entry)
        db.session.commit()
    except Exception as e: db.session.rollback()

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.path.startswith('/api/'): return jsonify({'error': 'Unauthorized'}), 401
                flash('Please log in first.', 'warning'); return redirect(url_for('login'))
            if not current_user.has_role(*roles):
                if request.path.startswith('/api/'): return jsonify({'error': 'Forbidden'}), 403
                flash('Access denied: Insufficient permissions.', 'danger'); return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# --- VALIDATORS ---
def valid_email(e): return bool(re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', e or ''))
def valid_phone(p): return bool(re.match(r'^\+?[0-9\s\-\(\)]{7,20}$', p or ''))
def valid_pwd(p):
    if not p or len(p) < 8: return False, "Password must be at least 8 characters."
    if not (re.search(r'[A-Z]', p) and re.search(r'[a-z]', p) and re.search(r'[0-9]', p) and re.search(r'[!@#$%^&*(),.?":{}|<>]', p)):
        return False, "Password requires uppercase, lowercase, digit, and special symbol."
    return True, None

# --- BASIC HTML LAYOUT & TEMPLATES ---
BASE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>AcxiomCRM</title>
    <style>
        body { font-family: sans-serif; margin: 0; padding: 0; background: #f4f6f8; color: #333; }
        header { background: #2c3e50; color: #fff; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; }
        header a { color: #fff; text-decoration: none; font-weight: bold; margin-right: 15px; }
        .container { padding: 20px; max-width: 1100px; margin: 0 auto; }
        .card { background: #fff; border: 1px solid #ccc; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: #fff; }
        th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
        th { background: #eaeded; }
        .badge { padding: 3px 7px; border-radius: 3px; font-size: 12px; background: #7f8c8d; color: #fff; }
        .bg-green { background: #27ae60; } .bg-blue { background: #2980b9; } .bg-orange { background: #e67e22; } .bg-red { background: #c0392b; }
        .alert { padding: 10px; margin-bottom: 15px; border-radius: 3px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
        .btn { padding: 6px 12px; background: #3498db; color: #fff; border: none; border-radius: 3px; cursor: pointer; text-decoration: none; font-size: 13px; display: inline-block; }
        .btn-success { background: #2ecc71; } .btn-danger { background: #e74c3c; } .btn-secondary { background: #95a5a6; }
        form label { display: block; margin-top: 10px; font-weight: bold; font-size: 14px; }
        form input, form select, form textarea { width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 3px; }
        .kpi-box { display: inline-block; width: 18%; background: #fff; border: 1px solid #ccc; padding: 12px; box-sizing: border-box; text-align: center; margin-right: 1.5%; border-top: 4px solid #3498db; }
    </style>
</head>
<body>
    <header>
        <div>
            <a href="/" style="font-size:18px;">AcxiomCRM</a>
            {% if current_user.is_authenticated %}
                <a href="/">Dashboard</a>
                <a href="/customers">Customers</a>
                <a href="/leads">Leads</a>
                <a href="/opportunities">Opportunities</a>
                <a href="/followups">Follow-Ups</a>
                {% if current_user.has_role('Admin', 'Manager') %}
                    <a href="/reports">Reports</a>
                    <a href="/audit-logs">Audit Logs</a>
                {% endif %}
                {% if current_user.has_role('Admin') %}
                    <a href="/users">Users</a>
                {% endif %}
            {% endif %}
        </div>
        <div>
            {% if current_user.is_authenticated %}
                <span style="font-size:13px;">Logged in: <b>{{ current_user.username }}</b> ({{ current_user.role }})</span>
                <a href="/logout" style="margin-left:15px; color:#ff7675;">Logout</a>
            {% else %}
                <a href="/login">Login</a>
            {% endif %}
        </div>
    </header>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for cat, msg in messages %}
                    <div class="alert alert-{{ cat }}">{{ msg }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>"""

def render_page(template_body, **kwargs):
    full_html = BASE_HTML.replace('{% block content %}{% endblock %}', template_body)
    return render_template_string(full_html, **kwargs)

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        u_str = request.form.get('username', '').strip()
        p_str = request.form.get('password', '')
        user = User.query.filter((User.username == u_str) | (User.email == u_str)).first()
        if user:
            if user.is_locked:
                if user.locked_until and datetime.utcnow() > user.locked_until:
                    user.is_locked = False; user.failed_attempts = 0; db.session.commit()
                else:
                    flash('Account is locked due to 5 failed attempts.', 'danger'); return redirect(url_for('login'))
            if not user.is_active: flash('Account deactivated.', 'danger'); return redirect(url_for('login'))
            if user.check_password(p_str):
                user.failed_attempts = 0; db.session.commit()
                login_user(user)
                log_audit('LOGIN_SUCCESS', 'Auth', record_id=user.id)
                return redirect(url_for('dashboard'))
            else:
                user.failed_attempts += 1
                if user.failed_attempts >= 5:
                    user.is_locked = True; user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                    log_audit('ACCOUNT_LOCKED', 'Auth', record_id=user.id, result='Failure')
                    flash('Account locked after 5 failed attempts.', 'danger')
                else:
                    log_audit('LOGIN_FAILURE', 'Auth', record_id=user.id, result='Failure')
                    flash(f'Invalid credentials. {5 - user.failed_attempts} attempts left.', 'danger')
                db.session.commit()
        else:
            log_audit('LOGIN_FAILURE', 'Auth', result='Failure')
            flash('Invalid credentials.', 'danger')
    return render_page("""
    <div style="max-width:350px; margin: 50px auto;" class="card">
        <h3>AcxiomCRM Login</h3>
        <form method="POST">
            <label>Username / Email</label><input type="text" name="username" required>
            <label>Password</label><input type="password" name="password" required>
            <br><br><button type="submit" class="btn" style="width:100%;">Log In</button>
        </form>
    </div>""")

@app.route('/logout')
@login_required
def logout():
    log_audit('LOGOUT', 'Auth', record_id=current_user.id)
    logout_user(); flash('Logged out.', 'success'); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    dr = request.args.get('date_range', 'all')
    cq, lq, oq, fq = Customer.query, Lead.query, Opportunity.query, FollowUp.query
    if current_user.role == 'Sales Executive':
        cq = cq.filter_by(assigned_to_id=current_user.id)
        lq = lq.filter_by(assigned_to_id=current_user.id)
        oq = oq.filter_by(owner_id=current_user.id)
        fq = fq.filter_by(assigned_to_id=current_user.id)

    tot_cust = cq.count()
    op_leads = lq.filter(Lead.status.in_(['New', 'Contacted', 'Qualified'])).count()
    act_opps = oq.filter(Opportunity.stage.in_(['Qualification', 'Proposal', 'Negotiation'])).all()
    pend_fol = fq.filter_by(status='Planned').count()
    tot_pipe = sum(o.amount for o in act_opps)
    w_pipe = sum(o.weighted_pipeline for o in act_opps)

    return render_page("""
    <h2>Executive Dashboard</h2>
    <div style="margin-bottom:15px;">
        <div class="kpi-box"><h4>Customers</h4><h2>{{ tot_cust }}</h2></div>
        <div class="kpi-box"><h4>Open Leads</h4><h2>{{ op_leads }}</h2></div>
        <div class="kpi-box"><h4>Active Opps</h4><h2>{{ act_opps|length }}</h2></div>
        <div class="kpi-box"><h4>Follow-Ups</h4><h2>{{ pend_fol }}</h2></div>
        <div class="kpi-box"><h4>Weighted Pipeline</h4><h2>${{ "%.2f"|format(w_pipe) }}</h2></div>
    </div>
    <div class="card">
        <h3>Pipeline Overview</h3>
        <p><b>Total Active Pipeline:</b> ${{ "%.2f"|format(tot_pipe) }} &bull; <b>Weighted Value:</b> ${{ "%.2f"|format(w_pipe) }}</p>
    </div>""", tot_cust=tot_cust, op_leads=op_leads, act_opps=act_opps, pend_fol=pend_fol, tot_pipe=tot_pipe, w_pipe=w_pipe)

# --- CUSTOMERS ---
@app.route('/customers')
@login_required
def customers():
    q = Customer.query
    if current_user.role == 'Sales Executive': q = q.filter_by(assigned_to_id=current_user.id)
    custs = q.order_by(Customer.created_at.desc()).all()
    return render_page("""
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2>Customers</h2><a href="/customers/create" class="btn btn-success">+ Add Customer</a>
    </div>
    <table>
        <tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Status</th><th>Assigned Exec</th><th>Actions</th></tr>
        {% for c in custs %}
        <tr>
            <td>#{{ c.id }}</td><td><b>{{ c.name }}</b></td><td>{{ c.email }}</td><td>{{ c.phone }}</td>
            <td><span class="badge bg-green">{{ c.status }}</span></td><td>{{ c.assigned_user.username if c.assigned_user else 'Unassigned' }}</td>
            <td><a href="/customers/{{ c.id }}" class="btn">View / Edit</a></td>
        </tr>
        {% else %}<tr><td colspan="7">No customer records.</td></tr>{% endfor %}
    </table>""", custs=custs)

@app.route('/customers/create', methods=['GET', 'POST'])
@app.route('/customers/<int:id>', methods=['GET', 'POST'])
@login_required
def customer_form(id=None):
    c = Customer.query.get_or_404(id) if id else None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        status = request.form.get('status', 'Active')
        notes = request.form.get('notes', '')

        if not name or not valid_email(email) or not valid_phone(phone):
            flash('Invalid name, email, or phone format.', 'danger')
        elif Customer.query.filter(Customer.email == email, Customer.id != (c.id if c else 0)).first():
            flash('Customer with this email already exists.', 'danger')
        elif Customer.query.filter(Customer.phone == phone, Customer.id != (c.id if c else 0)).first():
            flash('Customer with this phone number already exists.', 'danger')
        else:
            if not c:
                c = Customer(name=name, email=email, phone=phone, status=status, notes=notes, assigned_to_id=current_user.id, created_by_id=current_user.id)
                db.session.add(c); db.session.commit()
                log_audit('CREATE_CUSTOMER', 'Customer', record_id=c.id)
                flash('Customer created.', 'success')
            else:
                c.name, c.email, c.phone, c.status, c.notes = name, email, phone, status, notes
                db.session.commit()
                log_audit('UPDATE_CUSTOMER', 'Customer', record_id=c.id)
                flash('Customer updated.', 'success')
            return redirect(url_for('customers'))

    return render_page("""
    <h2>{{ 'Edit Customer' if c else 'Add Customer' }}</h2>
    <div class="card" style="max-width:600px;">
        <form method="POST">
            <label>Customer Name *</label><input type="text" name="name" value="{{ c.name if c else '' }}" required>
            <label>Email *</label><input type="email" name="email" value="{{ c.email if c else '' }}" required>
            <label>Phone *</label><input type="text" name="phone" value="{{ c.phone if c else '' }}" required>
            <label>Status</label><select name="status"><option value="Active" {% if c and c.status=='Active' %}selected{% endif %}>Active</option><option value="Inactive" {% if c and c.status=='Inactive' %}selected{% endif %}>Inactive</option></select>
            <label>Notes</label><textarea name="notes" rows="3">{{ c.notes if c else '' }}</textarea>
            <br><br><button type="submit" class="btn btn-success">Save Customer</button> <a href="/customers" class="btn btn-secondary">Cancel</a>
        </form>
    </div>""", c=c)

# --- LEADS ---
@app.route('/leads')
@login_required
def leads():
    q = Lead.query
    if current_user.role == 'Sales Executive': q = q.filter_by(assigned_to_id=current_user.id)
    lds = q.order_by(Lead.created_at.desc()).all()
    return render_page("""
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2>Leads</h2><a href="/leads/create" class="btn btn-success">+ Capture Lead</a>
    </div>
    <table>
        <tr><th>ID</th><th>Contact Name</th><th>Company</th><th>Email</th><th>Status</th><th>Priority</th><th>Actions</th></tr>
        {% for l in lds %}
        <tr>
            <td>#{{ l.id }}</td><td><b>{{ l.contact_name }}</b></td><td>{{ l.company_name or '-' }}</td><td>{{ l.email }}</td>
            <td><span class="badge bg-blue">{{ l.status }}</span></td><td>{{ l.priority }}</td>
            <td>
                <a href="/leads/{{ l.id }}" class="btn">Edit</a>
                {% if l.status == 'Qualified' %}<a href="/leads/{{ l.id }}/convert" class="btn btn-success">Convert</a>{% endif %}
            </td>
        </tr>
        {% else %}<tr><td colspan="7">No lead records.</td></tr>{% endfor %}
    </table>""", lds=lds)

@app.route('/leads/create', methods=['GET', 'POST'])
@app.route('/leads/<int:id>', methods=['GET', 'POST'])
@login_required
def lead_form(id=None):
    l = Lead.query.get_or_404(id) if id else None
    if request.method == 'POST':
        name = request.form.get('contact_name', '').strip()
        comp = request.form.get('company_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        status = request.form.get('status', 'New')
        priority = request.form.get('priority', 'Medium')
        notes = request.form.get('notes', '')

        if not name or not valid_email(email) or not valid_phone(phone):
            flash('Invalid contact name, email, or phone format.', 'danger')
        else:
            if not l:
                l = Lead(contact_name=name, company_name=comp, email=email, phone=phone, status=status, priority=priority, notes=notes, assigned_to_id=current_user.id, created_by_id=current_user.id)
                db.session.add(l); db.session.commit()
                log_audit('CREATE_LEAD', 'Lead', record_id=l.id); flash('Lead captured.', 'success')
            else:
                l.contact_name, l.company_name, l.email, l.phone, l.status, l.priority, l.notes = name, comp, email, phone, status, priority, notes
                db.session.commit()
                log_audit('UPDATE_LEAD', 'Lead', record_id=l.id); flash('Lead updated.', 'success')
            return redirect(url_for('leads'))

    return render_page("""
    <h2>{{ 'Edit Lead' if l else 'Capture Lead' }}</h2>
    <div class="card" style="max-width:600px;">
        <form method="POST">
            <label>Contact Name *</label><input type="text" name="contact_name" value="{{ l.contact_name if l else '' }}" required>
            <label>Company</label><input type="text" name="company_name" value="{{ l.company_name if l else '' }}">
            <label>Email *</label><input type="email" name="email" value="{{ l.email if l else '' }}" required>
            <label>Phone *</label><input type="text" name="phone" value="{{ l.phone if l else '' }}" required>
            <label>Status</label><select name="status">
                {% for st in ['New', 'Contacted', 'Qualified', 'Unqualified', 'Converted', 'Lost'] %}
                    <option value="{{ st }}" {% if l and l.status==st %}selected{% endif %}>{{ st }}</option>
                {% endfor %}
            </select>
            <label>Priority</label><select name="priority">
                {% for pr in ['Low', 'Medium', 'High'] %}
                    <option value="{{ pr }}" {% if l and l.priority==pr %}selected{% endif %}>{{ pr }}</option>
                {% endfor %}
            </select>
            <label>Notes</label><textarea name="notes" rows="3">{{ l.notes if l else '' }}</textarea>
            <br><br><button type="submit" class="btn btn-success">Save Lead</button> <a href="/leads" class="btn btn-secondary">Cancel</a>
        </form>
    </div>""", l=l)

@app.route('/leads/<int:id>/convert', methods=['GET', 'POST'])
@login_required
def convert_lead(id):
    l = Lead.query.get_or_404(id)
    if l.status == 'Converted': flash('Lead already converted.', 'warning'); return redirect(url_for('leads'))
    if request.method == 'POST':
        c = Customer(name=l.contact_name, email=l.email, phone=l.phone, status='Active', assigned_to_id=l.assigned_to_id or current_user.id, created_by_id=current_user.id, notes=f"Converted from Lead #{l.id}")
        db.session.add(c); db.session.flush()
        amt = float(request.form.get('amount', 5000))
        opp = Opportunity(name=f"Deal - {l.contact_name}", customer_id=c.id, owner_id=current_user.id, stage='Qualification', amount=amt, probability=20, expected_close_date=date.today()+timedelta(days=30))
        db.session.add(opp)
        l.status = 'Converted'
        db.session.commit()
        log_audit('CONVERT_LEAD', 'Lead', record_id=l.id, metadata={'customer_id': c.id, 'opp_id': opp.id})
        flash(f'Lead converted to Customer "{c.name}" and Opportunity created.', 'success')
        return redirect(url_for('customers'))
    return render_page("""
    <h2>Convert Lead #{{ l.id }} to Customer</h2>
    <div class="card" style="max-width:500px;">
        <p><b>Contact:</b> {{ l.contact_name }} &bull; <b>Email:</b> {{ l.email }}</p>
        <form method="POST">
            <label>Initial Opportunity Amount ($)</label><input type="number" step="0.01" name="amount" value="5000.00" required>
            <br><br><button type="submit" class="btn btn-success">Confirm Lead Conversion</button> <a href="/leads" class="btn btn-secondary">Cancel</a>
        </form>
    </div>""", l=l)

# --- OPPORTUNITIES ---
@app.route('/opportunities')
@login_required
def opportunities():
    q = Opportunity.query
    if current_user.role == 'Sales Executive': q = q.filter_by(owner_id=current_user.id)
    opps = q.order_by(Opportunity.created_at.desc()).all()
    return render_page("""
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2>Opportunities</h2><a href="/opportunities/create" class="btn btn-success">+ New Opportunity</a>
    </div>
    <table>
        <tr><th>ID</th><th>Opportunity Name</th><th>Customer</th><th>Stage</th><th>Amount ($)</th><th>Prob (%)</th><th>Weighted ($)</th><th>Actions</th></tr>
        {% for o in opps %}
        <tr>
            <td>#{{ o.id }}</td><td><b>{{ o.name }}</b></td><td>{{ o.customer.name if o.customer else 'N/A' }}</td>
            <td><span class="badge bg-orange">{{ o.stage }}</span></td><td>${{ "%.2f"|format(o.amount) }}</td><td>{{ o.probability }}%</td>
            <td><b>${{ "%.2f"|format(o.weighted_pipeline) }}</b></td>
            <td><a href="/opportunities/{{ o.id }}" class="btn">Edit</a></td>
        </tr>
        {% else %}<tr><td colspan="8">No sales opportunities.</td></tr>{% endfor %}
    </table>""", opps=opps)

@app.route('/opportunities/create', methods=['GET', 'POST'])
@app.route('/opportunities/<int:id>', methods=['GET', 'POST'])
@login_required
def opportunity_form(id=None):
    o = Opportunity.query.get_or_404(id) if id else None
    custs = Customer.query.filter_by(status='Active').all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        cid = request.form.get('customer_id', type=int)
        stage = request.form.get('stage', 'Qualification')
        amt = float(request.form.get('amount', 0))
        prob = float(request.form.get('probability', 0))
        dt_str = request.form.get('expected_close_date', '')

        try: exp_dt = datetime.strptime(dt_str, '%Y-%m-%d').date()
        except ValueError: exp_dt = None

        if not name or amt <= 0 or prob < 0 or prob > 100 or not exp_dt or (stage not in ['Won', 'Lost'] and exp_dt < date.today()):
            flash('Invalid opportunity details. Amount > 0, Prob 0-100%, and valid future date required.', 'danger')
        else:
            if not o:
                o = Opportunity(name=name, customer_id=cid, owner_id=current_user.id, stage=stage, amount=amt, probability=prob, expected_close_date=exp_dt)
                db.session.add(o); db.session.commit()
                log_audit('CREATE_OPPORTUNITY', 'Opportunity', record_id=o.id); flash('Opportunity created.', 'success')
            else:
                o.name, o.customer_id, o.stage, o.amount, o.probability, o.expected_close_date = name, cid, stage, amt, prob, exp_dt
                db.session.commit()
                log_audit('UPDATE_OPPORTUNITY', 'Opportunity', record_id=o.id); flash('Opportunity updated.', 'success')
            return redirect(url_for('opportunities'))

    return render_page("""
    <h2>{{ 'Edit Opportunity' if o else 'New Opportunity' }}</h2>
    <div class="card" style="max-width:600px;">
        <form method="POST">
            <label>Opportunity Name *</label><input type="text" name="name" value="{{ o.name if o else '' }}" required>
            <label>Customer Record</label><select name="customer_id"><option value="">-- None --</option>{% for c in custs %}<option value="{{ c.id }}" {% if o and o.customer_id==c.id %}selected{% endif %}>{{ c.name }}</option>{% endfor %}</select>
            <label>Stage</label><select name="stage">{% for st in ['Qualification', 'Proposal', 'Negotiation', 'Won', 'Lost'] %}<option value="{{ st }}" {% if o and o.stage==st %}selected{% endif %}>{{ st }}</option>{% endfor %}</select>
            <label>Deal Amount ($) *</label><input type="number" step="0.01" name="amount" value="{{ o.amount if o else '10000.00' }}" required>
            <label>Probability (%) *</label><input type="number" min="0" max="100" name="probability" value="{{ o.probability if o else '20' }}" required>
            <label>Expected Close Date *</label><input type="date" name="expected_close_date" value="{{ o.expected_close_date.strftime('%Y-%m-%d') if o else '' }}" required>
            <br><br><button type="submit" class="btn btn-success">Save Opportunity</button> <a href="/opportunities" class="btn btn-secondary">Cancel</a>
        </form>
    </div>""", o=o, custs=custs)

# --- FOLLOW-UPS ---
@app.route('/followups')
@login_required
def followups():
    q = FollowUp.query
    if current_user.role == 'Sales Executive': q = q.filter_by(assigned_to_id=current_user.id)
    fls = q.order_by(FollowUp.follow_up_date.asc()).all()
    return render_page("""
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2>Follow-Up Schedule</h2><a href="/followups/create" class="btn btn-success">+ Schedule Activity</a>
    </div>
    <table>
        <tr><th>Date & Time</th><th>Target</th><th>Subject</th><th>Type</th><th>Status</th><th>Action</th></tr>
        {% for f in fls %}
        <tr>
            <td>{{ f.follow_up_date.strftime('%Y-%m-%d %H:%M') }}</td><td>{{ f.target_type }} #{{ f.target_id }}</td><td><b>{{ f.subject }}</b></td>
            <td><span class="badge">{{ f.type }}</span></td><td><span class="badge bg-blue">{{ f.status }}</span></td>
            <td>{% if f.status == 'Planned' %}<a href="/followups/{{ f.id }}/complete" class="btn btn-success">Complete</a>{% endif %}</td>
        </tr>
        {% else %}<tr><td colspan="6">No follow-ups scheduled.</td></tr>{% endfor %}
    </table>""", fls=fls)

@app.route('/followups/create', methods=['GET', 'POST'])
@login_required
def followup_create():
    if request.method == 'POST':
        tt = request.form.get('target_type', 'Customer')
        tid = request.form.get('target_id', type=int)
        subj = request.form.get('subject', '').strip()
        ftype = request.form.get('type', 'Call')
        dt_str = request.form.get('follow_up_date', '')

        try: fdt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
        except ValueError: fdt = None

        if not subj or not tid or not fdt or (fdt < datetime.utcnow() - timedelta(minutes=5) and not current_user.has_role('Admin', 'Manager')):
            flash('Invalid date/time or subject. Future date required.', 'danger')
        else:
            f = FollowUp(target_type=tt, target_id=tid, subject=subj, type=ftype, follow_up_date=fdt, status='Planned', assigned_to_id=current_user.id)
            db.session.add(f); db.session.commit()
            log_audit('CREATE_FOLLOWUP', 'FollowUp', record_id=f.id); flash('Follow-up scheduled.', 'success')
            return redirect(url_for('followups'))

    return render_page("""
    <h2>Schedule Follow-Up Activity</h2>
    <div class="card" style="max-width:500px;">
        <form method="POST">
            <label>Target Entity Type</label><select name="target_type"><option value="Customer">Customer</option><option value="Lead">Lead</option><option value="Opportunity">Opportunity</option></select>
            <label>Target Record ID *</label><input type="number" name="target_id" value="1" required>
            <label>Subject / Agenda *</label><input type="text" name="subject" required>
            <label>Activity Type</label><select name="type"><option value="Call">Call</option><option value="Meeting">Meeting</option><option value="Email">Email</option><option value="Task">Task</option></select>
            <label>Scheduled Date & Time *</label><input type="datetime-local" name="follow_up_date" required>
            <br><br><button type="submit" class="btn btn-success">Schedule Activity</button> <a href="/followups" class="btn btn-secondary">Cancel</a>
        </form>
    </div>""")

@app.route('/followups/<int:id>/complete')
@login_required
def followup_complete(id):
    f = FollowUp.query.get_or_404(id)
    f.status = 'Completed'; db.session.commit()
    log_audit('UPDATE_FOLLOWUP_STATUS', 'FollowUp', record_id=f.id, metadata={'status': 'Completed'})
    flash('Follow-up marked completed.', 'success'); return redirect(url_for('followups'))

# --- USER MANAGEMENT (ADMIN ONLY) ---
@app.route('/users')
@login_required
@role_required('Admin')
def users():
    usrs = User.query.all()
    return render_page("""
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2>User Administration</h2><a href="/users/create" class="btn btn-success">+ Add User</a>
    </div>
    <table>
        <tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr>
        {% for u in usrs %}
        <tr>
            <td>#{{ u.id }}</td><td><b>{{ u.username }}</b></td><td>{{ u.email }}</td><td><span class="badge bg-red">{{ u.role }}</span></td>
            <td>{{ 'Active' if u.is_active else 'Deactivated' }} {{ '(Locked)' if u.is_locked else '' }}</td>
            <td>{% if u.is_locked %}<a href="/users/{{ u.id }}/unlock" class="btn btn-secondary">Unlock</a>{% endif %}</td>
        </tr>
        {% endfor %}
    </table>""", usrs=usrs)

@app.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def user_create():
    if request.method == 'POST':
        uname = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        pwd = request.form.get('password', '')
        role = request.form.get('role', 'Sales Executive')
        v_p, msg_p = valid_pwd(pwd)
        if not uname or not valid_email(email) or not v_p:
            flash(msg_p or 'Invalid username or email format.', 'danger')
        elif User.query.filter((User.username == uname) | (User.email == email)).first():
            flash('Username or email already registered.', 'danger')
        else:
            u = User(username=uname, email=email, role=role, is_active=True)
            u.set_password(pwd); db.session.add(u); db.session.commit()
            log_audit('CREATE_USER', 'User', record_id=u.id); flash(f'User "{uname}" created.', 'success')
            return redirect(url_for('users'))

    return render_page("""
    <h2>Create New User Account</h2>
    <div class="card" style="max-width:500px;">
        <form method="POST">
            <label>Username *</label><input type="text" name="username" required>
            <label>Email *</label><input type="email" name="email" required>
            <label>Password *</label><input type="password" name="password" required>
            <label>Primary Role</label><select name="role"><option value="Sales Executive">Sales Executive</option><option value="Manager">Manager</option><option value="Admin">Admin</option></select>
            <br><br><button type="submit" class="btn btn-success">Save User</button> <a href="/users" class="btn btn-secondary">Cancel</a>
        </form>
    </div>""")

@app.route('/users/<int:id>/unlock')
@login_required
@role_required('Admin')
def user_unlock(id):
    u = User.query.get_or_404(id)
    u.is_locked = False; u.failed_attempts = 0; u.locked_until = None; db.session.commit()
    log_audit('ADMIN_UNLOCK_USER', 'User', record_id=u.id); flash(f'User "{u.username}" unlocked.', 'success')
    return redirect(url_for('users'))

# --- AUDIT LOGS ---
@app.route('/audit-logs')
@login_required
@role_required('Admin', 'Manager')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_page("""
    <h2>Security & Activity Audit Trail</h2>
    <table>
        <tr><th>Timestamp</th><th>User</th><th>Module</th><th>Action</th><th>Record ID</th><th>Result</th></tr>
        {% for l in logs %}
        <tr>
            <td>{{ l.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td><td><b>{{ l.username }}</b></td>
            <td>{{ l.module }}</td><td><span class="badge">{{ l.action }}</span></td><td>{{ l.record_id or '-' }}</td>
            <td><span class="badge {{ 'bg-green' if l.result=='Success' else 'bg-red' }}">{{ l.result }}</span></td>
        </tr>
        {% endfor %}
    </table>""", logs=logs)

# --- REPORTS & CSV EXPORT ---
@app.route('/reports')
@login_required
@role_required('Admin', 'Manager')
def reports():
    return render_page("""
    <h2>Executive Reports & CSV Downloads</h2>
    <div class="card">
        <h3>Data Export Links</h3>
        <p>
            <a href="/reports/export/customers" class="btn btn-success">Export Customers CSV</a>
            <a href="/reports/export/leads" class="btn btn-success">Export Leads CSV</a>
            <a href="/reports/export/opportunities" class="btn btn-success">Export Opportunities CSV</a>
        </p>
    </div>""")

@app.route('/reports/export/<type>')
@login_required
@role_required('Admin', 'Manager')
def export_csv(type):
    si = StringIO(); cw = csv.writer(si)
    if type == 'customers':
        cw.writerow(['ID', 'Name', 'Email', 'Phone', 'Status']); [cw.writerow([c.id, c.name, c.email, c.phone, c.status]) for c in Customer.query.all()]
    elif type == 'leads':
        cw.writerow(['ID', 'Name', 'Company', 'Email', 'Status']); [cw.writerow([l.id, l.contact_name, l.company_name, l.email, l.status]) for l in Lead.query.all()]
    elif type == 'opportunities':
        cw.writerow(['ID', 'Name', 'Stage', 'Amount', 'Probability', 'Weighted']); [cw.writerow([o.id, o.name, o.stage, o.amount, o.probability, o.weighted_pipeline]) for o in Opportunity.query.all()]
    else: return "Invalid report", 400
    log_audit('EXPORT_REPORT', 'Report', metadata={'type': type})
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-disposition": f"attachment; filename={type}.csv"})

# --- REST API ---
@app.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    u = User.query.filter((User.username == data.get('username')) | (User.email == data.get('username'))).first()
    if u and u.check_password(data.get('password', '')) and u.is_active and not u.is_locked:
        login_user(u); return jsonify({'status': 'success', 'user': u.to_dict()}), 200
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/v1/customers', methods=['GET'])
@login_required
def api_customers(): return jsonify([c.to_dict() for c in Customer.query.all()]), 200

@app.route('/api/v1/leads', methods=['GET'])
@login_required
def api_leads(): return jsonify([l.to_dict() for l in Lead.query.all()]), 200

@app.route('/api/v1/opportunities', methods=['GET'])
@login_required
def api_opps(): return jsonify([o.to_dict() for o in Opportunity.query.all()]), 200

@app.route('/api/v1/followups', methods=['GET'])
@login_required
def api_followups(): return jsonify([f.to_dict() for f in FollowUp.query.all()]), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            from seed import seed_database
            seed_database(app)
    app.run(host='127.0.0.1', port=5000, debug=True)
