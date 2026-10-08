import re
from datetime import datetime, date

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
PHONE_REGEX = r'^\+?[0-9\s\-\(\)]{7,20}$'

def validate_email(email):
    if not email:
        return False, "Email address is required."
    if not re.match(EMAIL_REGEX, email.strip()):
        return False, "Invalid email format. (e.g. user@example.com)"
    return True, None

def validate_phone(phone):
    if not phone:
        return False, "Phone number is required."
    if not re.match(PHONE_REGEX, phone.strip()):
        return False, "Invalid phone number format. Must contain 7 to 20 digits/symbols."
    return True, None

def validate_password_strength(password):
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character (!@#$%^&*...)."
    return True, None

VALID_LEAD_TRANSITIONS = {
    'New': ['Contacted', 'Qualified', 'Unqualified', 'Lost'],
    'Contacted': ['Qualified', 'Unqualified', 'Lost'],
    'Qualified': ['Converted', 'Unqualified', 'Lost'],
    'Unqualified': ['Contacted', 'Qualified'],
    'Converted': [], # Terminal state
    'Lost': ['Contacted', 'Qualified'] # Re-engagement
}

def validate_lead_status_transition(current_status, new_status):
    if current_status == new_status:
        return True, None
    allowed = VALID_LEAD_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        return False, f"Invalid status transition from '{current_status}' to '{new_status}'. Allowed: {', '.join(allowed) if allowed else 'None (Terminal state)'}"
    return True, None

def validate_followup_date(dt_str, allow_past=False):
    if not dt_str:
        return False, "Follow-up date and time are required."
    try:
        # Accepts 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'
        if 'T' in dt_str:
            dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
        elif ' ' in dt_str:
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
        else:
            dt = datetime.strptime(dt_str, '%Y-%m-%d')
    except ValueError:
        return False, "Invalid date/time format. Expected YYYY-MM-DD HH:MM."
    
    if not allow_past:
        now = datetime.utcnow()
        # Allow up to 5 minutes margin for user system clock offset
        if (now - dt).total_seconds() > 300:
            return False, "New follow-up date cannot be earlier than today/current time."
    return True, dt

def validate_opportunity_fields(amount, probability, expected_close_date_str, is_active=True):
    try:
        amt = float(amount)
    except (ValueError, TypeError):
        return False, "Opportunity amount must be a valid number."
    
    if is_active and amt <= 0:
        return False, "Opportunity amount must be greater than 0 for active opportunities."
    
    try:
        prob = float(probability)
    except (ValueError, TypeError):
        return False, "Probability must be a valid number."
    
    if prob < 0 or prob > 100:
        return False, "Probability must be between 0 and 100."

    if not expected_close_date_str:
        return False, "Expected close date is required."

    try:
        exp_date = datetime.strptime(expected_close_date_str, '%Y-%m-%d').date()
    except ValueError:
        return False, "Expected close date format must be YYYY-MM-DD."

    if is_active and exp_date < date.today():
        return False, "Expected Close Date cannot be in the past for active opportunities."

    return True, (amt, prob, exp_date)
