# 🚀 AI Safety Systems - Production Deployment Guide

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
ai_safety_env\Scripts\activate  # Windows

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
