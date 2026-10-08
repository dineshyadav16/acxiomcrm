import json
from flask import request
from flask_login import current_user
from app.models import db, AuditLog

def log_audit(action, module, record_id=None, result='Success', metadata=None, user=None, ip_address=None):
    try:
        acting_user = user or (current_user if current_user.is_authenticated else None)
        user_id = acting_user.id if acting_user else None
        username = acting_user.username if acting_user else 'System/Anonymous'
        
        req_ip = ip_address
        if not req_ip and request:
            req_ip = request.remote_addr

        meta_str = None
        if metadata:
            if isinstance(metadata, (dict, list)):
                meta_str = json.dumps(metadata)
            else:
                meta_str = str(metadata)

        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            module=module,
            record_id=str(record_id) if record_id is not None else None,
            result=result,
            metadata_json=meta_str,
            ip_address=req_ip
        )
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Fallback print in dev if db write fails
        print(f"[AUDIT LOG ERROR] Failed to record audit log: {str(e)}")
