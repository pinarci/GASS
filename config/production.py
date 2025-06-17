# Production Configuration - config/production.py

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
LOGS_DIR = PROJECT_ROOT / "logs"

# Database configuration
DATABASE_CONFIG = {
    'users_db': PROJECT_ROOT / "production_users.db",
    'attendance_db': PROJECT_ROOT / "attendance_logs.db",
    'backup_dir': PROJECT_ROOT / "backups"
}

# Face recognition settings
FACE_RECOGNITION_CONFIG = {
    'known_faces_dir': STATIC_DIR / "known_faces",
    'confidence_threshold': 0.7,
    'tolerance': 0.6,
    'max_face_size': 1024,
    'cache_encodings': True
}

# Security settings
SECURITY_CONFIG = {
    'secret_key': os.environ.get('FLASK_SECRET_KEY', 'change-this-in-production'),
    'password_min_length': 8,
    'session_timeout_hours': 8,
    'max_login_attempts': 5
}

# Messaging settings
MESSAGING_CONFIG = {
    'enable_real_time': True,
    'message_retention_days': 365,
    'max_message_length': 1000,
    'enable_file_sharing': False
}

# GPS/Location settings
GPS_CONFIG = {
    'enable_tracking': True,
    'update_interval_seconds': 30,
    'geofence_radius_meters': 100
}

# School specific settings
SCHOOL_CONFIG = {
    'school_name': "Your School Name",
    'school_address': "School Address",
    'school_phone': "School Phone",
    'academic_year': "2024-2025",
    'timezone': "Europe/Istanbul"
}

# System limits
SYSTEM_LIMITS = {
    'max_students_per_vehicle': 30,
    'max_upload_size_mb': 10,
    'max_face_photos_per_student': 5
}
