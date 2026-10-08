import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'acxiomcrm-dev-secret-key-2026-secure')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///acxiomcrm.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Policy Configuration
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    PASSWORD_MIN_LENGTH = 8
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600 # 1 hour
