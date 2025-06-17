# Production Setup Script - setup_production.py

import os
import sys
from pathlib import Path
import shutil
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('setup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent


def setup_directory_structure():
    """Create production directory structure"""
    logger.info("🏗️ Setting up directory structure...")

    directories = [
        "static/known_faces",
        "static/uploads",
        "static/profile_photos",
        "logs",
        "backups",
        "sample_data",
        "userManagement",
        "messaging",
        "routes",
        "reports"
    ]

    for directory in directories:
        dir_path = PROJECT_ROOT / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"  ✅ Created: {directory}")

    logger.info("✅ Directory structure ready")


def create_production_config():
    """Create production configuration file"""
    logger.info("⚙️ Creating production configuration...")

    config_content = '''# Production Configuration - config/production.py

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
'''

    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(exist_ok=True)

    with open(config_dir / "production.py", 'w', encoding='utf-8') as f:
        f.write(config_content)

    logger.info("✅ Production config created")


def create_deployment_guide():
    """Create deployment guide"""
    logger.info("📖 Creating deployment guide...")

    guide_content = '''# 🚀 AI Safety Systems - Production Deployment Guide

## Prerequisites

### System Requirements
- Python 3.8 or higher
- OpenCV 4.0+
- dlib (for face recognition)
- SQLite 3
- Minimum 4GB RAM
- 50GB storage space

### Hardware Requirements
- USB/IP cameras for vehicles
- GPS tracking devices (optional)
- Tablets/smartphones for drivers
- Server/VPS for hosting

## Installation Steps

### 1. Environment Setup
```bash
# Create virtual environment
python3 -m venv ai_safety_env
source ai_safety_env/bin/activate  # Linux/Mac
# or
ai_safety_env\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Run setup script
python setup_production.py

# Import real user data
python -c "
from userManagement.userManager import user_manager
user_manager.import_users_from_csv('sample_data/users.csv')
"
```

### 3. Face Recognition Setup
```bash
# Add student photos to static/known_faces/
# Structure: static/known_faces/StudentName/photo1.jpg

# Build face encodings
python -c "
from attendance.faceRecognition import rebuild_face_encodings
rebuild_face_encodings()
"
```

### 4. Configuration
```bash
# Edit config/production.py with your settings
# Set environment variables:
export FLASK_SECRET_KEY="your-super-secret-key"
export FLASK_ENV="production"
```

### 5. Run Production Server
```bash
# Using Gunicorn (recommended)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app

# Or with Flask (development only)
python main.py
```

## Data Import Process

### 1. Prepare User Data (CSV Format)
```csv
username,password,role,full_name,email,phone
john.doe,password123,parent,John Doe,john@email.com,555-1234
jane.driver,driver456,driver,Jane Smith,jane@school.edu,555-5678
```

### 2. Prepare Student Data (CSV Format)
```csv
student_id,full_name,class_name,parent_username,emergency_contact,pickup_address
STU001,Alice Doe,4-A,john.doe,555-1235,123 Main St
STU002,Bob Smith,3-B,mary.parent,555-5679,456 Oak Ave
```

### 3. Add Student Photos
- Create folder: `static/known_faces/StudentFullName/`
- Add 3-5 clear photos of each student
- Supported formats: JPG, PNG
- Recommended: 512x512 pixels, good lighting

### 4. Import Data
```python
from userManagement.userManager import user_manager

# Import users
user_manager.import_users_from_csv('your_users.csv')

# Add students (example)
user_manager.add_student(
    student_id='STU001',
    full_name='Alice Doe',
    class_name='4-A',
    parent_username='john.doe',
    pickup_address='123 Main St'
)
```

## Security Checklist

### Production Security
- [ ] Change default secret key
- [ ] Use HTTPS in production
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Implement rate limiting
- [ ] Set up monitoring/logging
- [ ] Regular security updates

### Data Protection
- [ ] Student photo encryption
- [ ] GDPR compliance measures
- [ ] Data retention policies
- [ ] Access control auditing
- [ ] Backup encryption

## Monitoring & Maintenance

### Daily Tasks
- Check system logs
- Verify face recognition accuracy
- Monitor database size
- Check message delivery

### Weekly Tasks
- Review user activity
- Check vehicle GPS status
- Analyze attendance patterns
- Update student rosters

### Monthly Tasks
- Database backup verification
- Security audit
- Performance optimization
- User access review

## Troubleshooting

### Common Issues
1. **Face recognition not working**
   - Check photo quality and lighting
   - Verify face encoding cache
   - Review confidence thresholds

2. **Login issues**
   - Check user credentials in database
   - Verify password hashing
   - Check session configuration

3. **Performance issues**
   - Monitor database query performance
   - Check face encoding cache
   - Review server resources

### Support Contacts
- Technical Support: [Your contact info]
- Emergency Contact: [Your emergency contact]
- Documentation: [Your documentation URL]

## Backup & Recovery

### Automated Backups
```bash
# Daily database backup
python scripts/backup_database.py

# Weekly full system backup
python scripts/full_backup.py
```

### Recovery Procedures
1. Stop the application
2. Restore database from backup
3. Verify data integrity
4. Restart application
5. Test all functionality

## Legal & Compliance

### Required Documentation
- [ ] Privacy policy for parents
- [ ] Data processing agreements
- [ ] Student photo consent forms
- [ ] Security incident procedures
- [ ] Data retention schedule

### Compliance Requirements
- [ ] GDPR (EU) compliance
- [ ] COPPA (US) compliance
- [ ] Local education regulations
- [ ] Data protection laws
'''

    with open(PROJECT_ROOT / "DEPLOYMENT_GUIDE.md", 'w', encoding='utf-8') as f:
        f.write(guide_content)

    logger.info("✅ Deployment guide created")


def create_requirements_file():
    """Create production requirements.txt"""
    logger.info("📦 Creating requirements.txt...")

    requirements = '''# AI Safety Systems - Production Requirements

# Core Framework
Flask==2.3.3
Werkzeug==2.3.7

# Face Recognition
face-recognition==1.3.0
opencv-python==4.8.1.78
dlib==19.24.2
Pillow==10.0.1

# Database
sqlite3

# Security
bcrypt==4.0.1

# Data Processing
pandas==2.1.3
numpy==1.24.3

# Image Processing
scikit-image==0.21.0

# Utilities
python-dateutil==2.8.2
pytz==2023.3

# Production Server
gunicorn==21.2.0

# Optional: GPS/Location
# geopy==2.4.0
# folium==0.14.0

# Optional: Real-time messaging
# flask-socketio==5.3.6
# eventlet==0.33.3

# Development (remove in production)
# pytest==7.4.3
# pytest-flask==1.3.0
'''

    with open(PROJECT_ROOT / "requirements.txt", 'w', encoding='utf-8') as f:
        f.write(requirements)

    logger.info("✅ Requirements file created")


def setup_sample_data():
    """Create sample data for testing"""
    logger.info("📝 Creating sample data...")

    # Import user manager
    sys.path.append(str(PROJECT_ROOT))
    from userManagement.userManager import user_manager

    # Create sample CSV files
    users_csv, students_csv = user_manager.create_sample_data_csv()

    logger.info(f"✅ Sample data created:")
    logger.info(f"   Users: {users_csv}")
    logger.info(f"   Students: {students_csv}")


def create_backup_script():
    """Create backup script"""
    logger.info("💾 Creating backup script...")

    backup_script = '''#!/usr/bin/env python3
# Automatic Backup Script - scripts/backup_system.py

import sqlite3
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = PROJECT_ROOT / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_databases():
    """Backup all databases"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Backup user database
    user_db = PROJECT_ROOT / "production_users.db"
    if user_db.exists():
        backup_path = BACKUP_DIR / f"users_backup_{timestamp}.db"
        shutil.copy2(user_db, backup_path)
        logger.info(f"✅ User database backed up: {backup_path}")

    # Backup face encodings cache
    cache_file = PROJECT_ROOT / "face_encodings_cache.pkl"
    if cache_file.exists():
        backup_cache = BACKUP_DIR / f"face_cache_backup_{timestamp}.pkl"
        shutil.copy2(cache_file, backup_cache)
        logger.info(f"✅ Face cache backed up: {backup_cache}")

def backup_photos():
    """Backup student photos"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photos_dir = PROJECT_ROOT / "static" / "known_faces"

    if photos_dir.exists():
        backup_zip = BACKUP_DIR / f"photos_backup_{timestamp}.zip"

        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in photos_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(photos_dir)
                    zipf.write(file_path, arcname)

        logger.info(f"✅ Photos backed up: {backup_zip}")

def cleanup_old_backups(days_to_keep=30):
    """Remove backups older than specified days"""
    cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

    for backup_file in BACKUP_DIR.glob("*"):
        if backup_file.stat().st_mtime < cutoff_time:
            backup_file.unlink()
            logger.info(f"🗑️ Removed old backup: {backup_file}")

if __name__ == "__main__":
    logger.info("🔄 Starting system backup...")
    backup_databases()
    backup_photos()
    cleanup_old_backups()
    logger.info("✅ Backup completed!")
'''

    scripts_dir = PROJECT_ROOT / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    with open(scripts_dir / "backup_system.py", 'w', encoding='utf-8') as f:
        f.write(backup_script)

    logger.info("✅ Backup script created")


def main():
    """Main setup function"""
    logger.info("🚀 Starting AI Safety Systems Production Setup")
    logger.info("=" * 60)

    try:
        # Step 1: Directory structure
        setup_directory_structure()

        # Step 2: Configuration
        create_production_config()

        # Step 3: Documentation
        create_deployment_guide()

        # Step 4: Requirements
        create_requirements_file()

        # Step 5: Sample data
        setup_sample_data()

        # Step 6: Backup system
        create_backup_script()

        logger.info("=" * 60)
        logger.info("🎉 Production setup completed successfully!")
        logger.info("")
        logger.info("📋 Next Steps:")
        logger.info("1. Install requirements: pip install -r requirements.txt")
        logger.info("2. Add student photos to static/known_faces/")
        logger.info("3. Edit config/production.py with your settings")
        logger.info("4. Import real user data from CSV")
        logger.info("5. Run face encoding build")
        logger.info("6. Start production server")
        logger.info("")
        logger.info("📖 Read DEPLOYMENT_GUIDE.md for detailed instructions")

    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)