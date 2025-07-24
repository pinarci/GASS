import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json
from functools import wraps
import threading
import time

import googlemaps
import requests
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

# Project root is where this file is located
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import requests

# Import our enhanced modules (optional - fallback if not available)
try:
    from attendance.faceRecognition import load_known_faces, verify_student, get_face_recognition_stats
    from dataManagement.attendanceLogger import log_attendance, get_today_attendance, _init_today_attendance
except ImportError as e:
    print(f"⚠️ Some modules not found: {e}")
    print("Using fallback implementations...")

# Flask setup with real-time capabilities
app = Flask(__name__,
            template_folder=str(PROJECT_ROOT / "templates"),
            static_folder=str(PROJECT_ROOT / "static"))
app.secret_key = 'ai-safety-systems-production-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize SocketIO for real-time features
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Database paths
USERS_DB = PROJECT_ROOT / "production_users.db"
LOGIN_USERS_DB = PROJECT_ROOT / "loginusers.db"
STUDENTS_DB = PROJECT_ROOT / "students.db"
MESSAGES_DB = PROJECT_ROOT / "messages.db"
UPLOAD_FOLDER = PROJECT_ROOT / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


#Mustafa rota
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ORS_API_KEY = os.getenv("ORS_API_KEY")

# Add this line:
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

# Add these helper functions to your main.py (keep your existing functions and just add these)
def get_google_directions(origin, destination, waypoints):
    """Simple Google Maps directions - based on your working version"""
    try:
        directions = gmaps.directions(
            origin,
            destination,
            mode="driving",
            waypoints=waypoints,
            optimize_waypoints=True,
            departure_time=datetime.now()
        )
        if not directions:
            return None
        polyline = directions[0]['overview_polyline']['points']
        duration = sum(leg['duration']['value'] for leg in directions[0]['legs'])
        return {"source": "google", "polyline": polyline, "duration": duration}
    except Exception as e:
        print(f"Google Maps error: {e}")
        return None

def get_ors_directions(origin, destination, waypoints):
    """Simple ORS directions - based on your working version"""
    try:
        coordinates = [origin] + waypoints + [destination] if waypoints else [origin, destination]
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
        data = {
            "coordinates": [],
            "instructions": False,
        }
        
        # Use geopy for geocoding with longer timeout
        geolocator = Nominatim(user_agent="route_planner", timeout=10)
        for address in coordinates:
            try:
                location = geolocator.geocode(address, timeout=10)
                if not location:
                    print(f"Could not geocode: {address}")
                    return None
                data["coordinates"].append([location.longitude, location.latitude])
            except Exception as geo_error:
                print(f"Geocoding error for {address}: {geo_error}")
                return None
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"ORS error: {response.text}")
            return None
        
        result = response.json()
        polyline = result['routes'][0]['geometry']
        duration = result['routes'][0]['summary']['duration']
        return {"source": "ors", "polyline": polyline, "duration": duration}
    except Exception as e:
        print(f"ORS error: {e}")
        return None
#Mustafa rota



class RealTimeLocationService:
    """Real-time location tracking service"""

    def __init__(self):
        self.vehicle_locations = {}
        self.location_updates = []
        self.tracking_active = True

    def start_tracking(self):
        """Start background location tracking simulation"""

        def update_locations():
            while self.tracking_active:
                self.simulate_vehicle_movement()
                time.sleep(5)  # Update every 5 seconds

        tracking_thread = threading.Thread(target=update_locations, daemon=True)
        tracking_thread.start()

    def simulate_vehicle_movement(self):
        """Simulate realistic vehicle movement"""
        # Get active vehicles from database
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.id, v.license_plate, v.driver_id, u.full_name
            FROM vehicles v
            JOIN users u ON v.driver_id = u.id
            WHERE v.is_active = 1
        ''')
        vehicles = cursor.fetchall()
        conn.close()

        for vehicle in vehicles:
            vehicle_id, plate, driver_id, driver_name = vehicle

            # Get or initialize location
            if vehicle_id not in self.vehicle_locations:
                # Initialize with a realistic starting point (Ankara coordinates)
                self.vehicle_locations[vehicle_id] = {
                    'latitude': 39.9334 + (hash(str(vehicle_id)) % 100) * 0.001,
                    'longitude': 32.8597 + (hash(str(vehicle_id)) % 100) * 0.001,
                    'speed': 0,
                    'heading': 0,
                    'last_update': datetime.now().isoformat()
                }

            # Simulate movement (small increments)
            import random
            current = self.vehicle_locations[vehicle_id]

            # Simulate realistic city driving
            speed = random.randint(15, 45)  # km/h
            heading_change = random.randint(-15, 15)  # degrees

            # Convert speed to coordinate changes (very rough approximation)
            lat_change = (speed * 0.00001) * random.choice([-1, 1])
            lng_change = (speed * 0.00001) * random.choice([-1, 1])

            self.vehicle_locations[vehicle_id].update({
                'latitude': current['latitude'] + lat_change,
                'longitude': current['longitude'] + lng_change,
                'speed': speed,
                'heading': (current['heading'] + heading_change) % 360,
                'last_update': datetime.now().isoformat()
            })

            # Store in database
            conn = sqlite3.connect(USERS_DB)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE vehicles 
                SET current_latitude = ?, current_longitude = ?, last_location_update = ?
                WHERE id = ?
            ''', (
                self.vehicle_locations[vehicle_id]['latitude'],
                self.vehicle_locations[vehicle_id]['longitude'],
                datetime.now(),
                vehicle_id
            ))
            conn.commit()
            conn.close()

            # Emit to connected clients
            socketio.emit('location_update', {
                'vehicle_id': vehicle_id,
                'plate': plate,
                'driver_name': driver_name,
                **self.vehicle_locations[vehicle_id]
            }, room='location_tracking')

    def get_vehicle_location(self, vehicle_id):
        """Get current location of specific vehicle"""
        return self.vehicle_locations.get(vehicle_id)


class RealTimeMessaging:
    """Enhanced real-time messaging system"""

    @staticmethod
    def send_message(sender_id, receiver_id, message_text, message_type='text'):
        """Send real message with real-time delivery"""
        try:
            conn = sqlite3.connect(USERS_DB)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO messages (sender_id, receiver_id, message_text, message_type)
                VALUES (?, ?, ?, ?)
            ''', (sender_id, receiver_id, message_text, message_type))

            message_id = cursor.lastrowid

            # Get sender and receiver info
            cursor.execute('''
                SELECT full_name, role FROM users WHERE id = ?
            ''', (sender_id,))
            sender_info = cursor.fetchone()

            cursor.execute('''
                SELECT full_name, role FROM users WHERE id = ?
            ''', (receiver_id,))
            receiver_info = cursor.fetchone()

            conn.commit()

            # Create notification for receiver
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message, notification_type)
                VALUES (?, ?, ?, ?)
            ''', (receiver_id, 'Yeni Mesaj', f'{sender_info[0]} size mesaj gönderdi', 'message'))

            conn.commit()
            conn.close()

            # Real-time delivery via SocketIO
            socketio.emit('new_message', {
                'id': message_id,
                'sender_id': sender_id,
                'sender_name': sender_info[0],
                'sender_role': sender_info[1],
                'receiver_id': receiver_id,
                'message_text': message_text,
                'message_type': message_type,
                'sent_at': datetime.now().isoformat()
            }, room=f'user_{receiver_id}')

            # Also emit to sender for delivery confirmation
            socketio.emit('message_sent', {
                'message_id': message_id,
                'status': 'delivered'
            }, room=f'user_{sender_id}')

            print(f"✅ Real-time message sent: {sender_info[0]} → {receiver_info[0]}")
            return message_id

        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None


class SmartAttendanceSystem:
    """AI-powered attendance tracking"""

    @staticmethod
    def log_attendance(student_id, event_type, driver_id, confidence=0.95):
        """Log attendance with AI confidence score"""
        try:
            conn = sqlite3.connect(USERS_DB)
            cursor = conn.cursor()

            # Get student info
            cursor.execute('''
                SELECT s.full_name, s.parent_id, u.full_name as parent_name
                FROM students s
                JOIN users u ON s.parent_id = u.id
                WHERE s.id = ?
            ''', (student_id,))
            student_info = cursor.fetchone()

            if not student_info:
                return False

            student_name, parent_id, parent_name = student_info

            # Log attendance
            cursor.execute('''
                INSERT INTO attendance_logs (student_id, event_type, verified_by, confidence_score)
                VALUES (?, ?, ?, ?)
            ''', (student_id, event_type, driver_id, confidence))

            conn.commit()
            conn.close()

            # Real-time notification to parent
            event_messages = {
                'board': f'{student_name} otobüse bindi',
                'alight': f'{student_name} otobüsten indi',
                'present': f'{student_name} yoklamada mevcut',
                'absent': f'{student_name} bulunamadı'
            }

            socketio.emit('attendance_update', {
                'student_id': student_id,
                'student_name': student_name,
                'event_type': event_type,
                'message': event_messages.get(event_type, 'Durum güncellendi'),
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }, room=f'user_{parent_id}')

            print(f"✅ Attendance logged: {student_name} - {event_type}")
            return True

        except Exception as e:
            print(f"❌ Error logging attendance: {e}")
            return False


# Initialize services
location_service = RealTimeLocationService()
messaging_service = RealTimeMessaging()
attendance_service = SmartAttendanceSystem()


class EnhancedDatabase:
    """Enhanced database operations with real data"""

    def __init__(self):
        self.init_production_database()
        self.populate_sample_data()

    def init_production_database(self):
        """Initialize production database with enhanced schema"""
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()

        # Enhanced users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('parent', 'driver', 'admin')),
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                profile_photo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                online_status TEXT DEFAULT 'offline'
            )
        ''')

        # Enhanced students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                parent_id INTEGER,
                assigned_driver_id INTEGER,
                emergency_contact TEXT,
                pickup_address TEXT,
                dropoff_address TEXT,
                medical_notes TEXT,
                photo_path TEXT,
                is_active BOOLEAN DEFAULT 1,
                current_status TEXT DEFAULT 'at_home',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES users (id),
                FOREIGN KEY (assigned_driver_id) REFERENCES users (id)
            )
        ''')

        # Enhanced vehicles table with real-time tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_plate TEXT UNIQUE NOT NULL,
                driver_id INTEGER,
                capacity INTEGER NOT NULL,
                model TEXT,
                year INTEGER,
                current_latitude REAL,
                current_longitude REAL,
                current_speed REAL DEFAULT 0,
                current_heading REAL DEFAULT 0,
                last_location_update TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                status TEXT DEFAULT 'parked',
                FOREIGN KEY (driver_id) REFERENCES users (id)
            )
        ''')

        # Rest of the tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                event_type TEXT CHECK (event_type IN ('board', 'alight', 'present', 'absent')),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                location TEXT,
                confidence_score REAL DEFAULT 0.95,
                verified_by INTEGER,
                vehicle_id INTEGER,
                notes TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (verified_by) REFERENCES users (id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                is_read BOOLEAN DEFAULT 0,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP,
                attachment_path TEXT,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                notification_type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action_url TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ Enhanced database initialized")

    def populate_sample_data(self):
        """Populate with realistic sample data"""
        try:
            conn = sqlite3.connect(USERS_DB)
            cursor = conn.cursor()

            # Check if data already exists
            cursor.execute('SELECT COUNT(*) FROM users')
            if cursor.fetchone()[0] > 1:  # More than just admin
                conn.close()
                return

            # Create sample users
            users_data = [
                ('admin', generate_password_hash('admin123'), 'admin', 'Ahmet Yıldırım', 'admin@okul.edu.tr',
                 '0312 555 0001'),
                ('mehmet.kaya', generate_password_hash('driver123'), 'driver', 'Mehmet Kaya', 'mehmet@okul.edu.tr',
                 '0555 123 4567'),
                ('ali.ozcan', generate_password_hash('driver123'), 'driver', 'Ali Özcan', 'ali@okul.edu.tr',
                 '0555 234 5678'),
                ('ayse.yilmaz', generate_password_hash('parent123'), 'parent', 'Ayşe Yılmaz', 'ayse@email.com',
                 '0555 345 6789'),
                ('fatma.demir', generate_password_hash('parent123'), 'parent', 'Fatma Demir', 'fatma@email.com',
                 '0555 456 7890'),
                ('can.arslan', generate_password_hash('parent123'), 'parent', 'Can Arslan', 'can@email.com',
                 '0555 567 8901'),
            ]

            for username, password_hash, role, full_name, email, phone in users_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (username, password_hash, role, full_name, email, phone)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, password_hash, role, full_name, email, phone))

            # Create vehicles
            vehicles_data = [
                ('34 ABC 123', 2, 25, 'Mercedes Sprinter', 2020, 39.9334, 32.8597),
                ('34 DEF 456', 3, 30, 'Ford Transit', 2019, 39.9404, 32.8540),
            ]

            for plate, driver_id, capacity, model, year, lat, lng in vehicles_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO vehicles 
                    (license_plate, driver_id, capacity, model, year, current_latitude, current_longitude)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (plate, driver_id, capacity, model, year, lat, lng))

            # Create students
            students_data = [
                ('STU001', 'Zeynep Yılmaz', '4-A', 4, 2, '0555 999 0001', 'Kızılay Mah. No:15', 'X İlkokulu'),
                ('STU002', 'Ahmet Demir', '3-B', 5, 2, '0555 999 0002', 'Çankaya Mah. No:22', 'X İlkokulu'),
                ('STU003', 'Elif Özkan', '2-C', 6, 3, '0555 999 0003', 'Bahçelievler Mah. No:8', 'X İlkokulu'),
            ]

            for student_id, full_name, class_name, parent_id, driver_id, emergency, pickup, dropoff in students_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO students 
                    (student_id, full_name, class_name, parent_id, assigned_driver_id, emergency_contact, pickup_address, dropoff_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (student_id, full_name, class_name, parent_id, driver_id, emergency, pickup, dropoff))

            conn.commit()
            conn.close()
            print("✅ Sample data populated")

        except Exception as e:
            print(f"❌ Error populating data: {e}")


# Initialize enhanced database
db = EnhancedDatabase()


# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] != required_role:
                flash('Bu sayfaya erişim yetkiniz yok.', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ==================== MAIN ROUTES ====================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Kullanıcı adı ve şifre gereklidir.", "error")
            return render_template("login.html")

        # Authenticate user from loginusers.db
        conn = sqlite3.connect(LOGIN_USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT full_name, user_name, password, role
            FROM USERS 
            WHERE user_name = ?
        ''', (username,))

        user = cursor.fetchone()
        conn.close()

        if user and user[2] == password:  # Direct password comparison
            # Set session data
            session['user_id'] = username  # Using username as user_id since no ID in loginusers.db
            session['username'] = user[1]
            session['user_role'] = user[3]
            session['full_name'] = user[0]
            session['email'] = ""  # Not available in loginusers.db
            session['phone'] = ""  # Not available in loginusers.db

            flash(f"Hoş geldiniz, {user[0]}!", "success")

            # Role-based redirection
            if user[3] == 'parent':
                return redirect(url_for('parent_dashboard'))
            elif user[3] == 'driver':
                return redirect(url_for('driver_dashboard'))
            elif user[3] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Geçersiz kullanıcı rolü.", "error")
                return render_template("login.html")
        else:
            flash("Geçersiz kullanıcı adı veya şifre.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for('login'))


# ==================== PARENT ROUTES ====================

@app.route("/parent")
@login_required
@role_required('parent')
def parent_dashboard():
    """Enhanced parent dashboard with real data from students.db"""
    # Get student data from students.db based on parent's full_name
    conn = sqlite3.connect(STUDENTS_DB)
    cursor = conn.cursor()

    parent_full_name = session['full_name']
    
    # Find student whose father_name or mother_name matches the logged-in parent's full_name
    cursor.execute('''
        SELECT full_name, father_name, mother_name, class, gender, attendance
        FROM STUDENT 
        WHERE father_name = ? OR mother_name = ?
    ''', (parent_full_name, parent_full_name))

    student_data = cursor.fetchone()
    conn.close()

    # Prepare student information
    if student_data:
        # Determine status based on attendance
        if student_data[5]:  # attendance is True
            status_text = 'In the bus'
            status_class = 'status-on-bus'
        else:  # attendance is False
            status_text = 'At Home'
            status_class = 'status-at-home'
            
        student_info = {
            'name': student_data[0],
            'father_name': student_data[1],
            'mother_name': student_data[2],
            'class': student_data[3],
            'gender': student_data[4],
            'attendance': student_data[5],
            'status': status_text,
            'status_class': status_class,
            'last_activity': 'Bugün aktivite yok',
            'driver_name': 'Atanmamış',
            'driver_phone': 'N/A',
            'vehicle_plate': 'N/A'
        }
    else:
        # Default student info if no student found
        student_info = {
            'name': 'Öğrenci Bulunamadı',
            'father_name': '',
            'mother_name': '',
            'class': '',
            'gender': '',
            'attendance': False,
            'status': 'Unknown',
            'status_class': 'status-at-home',
            'last_activity': 'Veri yok',
            'driver_name': 'Atanmamış',
            'driver_phone': 'N/A',
            'vehicle_plate': 'N/A'
        }

    return render_template("parent.html",
                           user_name=session['full_name'],
                           student=student_info,
                           current_user={
                               'id': session['user_id'],
                               'name': session['full_name'],
                               'role': session['user_role']
                           })


# ==================== DRIVER ROUTES ====================

@app.route("/driver")
@login_required
@role_required('driver')
def driver_dashboard():
    """Enhanced driver dashboard with real data"""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()

    # Get assigned students
    cursor.execute('''
        SELECT s.id, s.full_name, s.class_name, s.current_status, s.pickup_address,
               p.full_name as parent_name, p.phone as parent_phone
        FROM students s
        LEFT JOIN users p ON s.parent_id = p.id
        WHERE s.assigned_driver_id = ? AND s.is_active = 1
        ORDER BY s.full_name
    ''', (session['user_id'],))

    students = []
    for student in cursor.fetchall():
        students.append({
            'id': student[0],
            'name': student[1],
            'class': student[2],
            'status': student[3],
            'address': student[4],
            'parent_name': student[5],
            'parent_phone': student[6]
        })

    # Get vehicle info
    cursor.execute('''
        SELECT license_plate, capacity, model, current_latitude, current_longitude
        FROM vehicles WHERE driver_id = ?
    ''', (session['user_id'],))

    vehicle = cursor.fetchone()
    vehicle_info = {
        'plate': vehicle[0] if vehicle else 'Araç Atanmamış',
        'capacity': vehicle[1] if vehicle else 0,
        'model': vehicle[2] if vehicle else 'N/A',
        'location': {'lat': vehicle[3], 'lng': vehicle[4]} if vehicle and vehicle[3] else None
    }

    conn.close()
    return render_template("driver.html",
                           user_name=session['full_name'],
                           vehicle=vehicle_info,
                           students=students,
                           current_user={
                               'id': session['user_id'],
                               'name': session['full_name'],
                               'role': session['user_role']
                           })









#Mustafa rota
# Update your existing driver-route route to include the API key

#Mustafa rota














@app.route("/driver-route")
@login_required
@role_required('driver')
def driver_route():
    """Enhanced driver route management page with parents.db integration"""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()

    # Get assigned students from main database
    cursor.execute('''
        SELECT s.id, s.full_name, s.class_name, s.current_status, s.pickup_address, s.dropoff_address,
               p.full_name as parent_name, p.phone as parent_phone
        FROM students s
        LEFT JOIN users p ON s.parent_id = p.id
        WHERE s.assigned_driver_id = ? AND s.is_active = 1
        ORDER BY s.full_name
    ''', (session['user_id'],))

    main_db_students = cursor.fetchall()

    # Get vehicle info
    cursor.execute('''
        SELECT id, license_plate, capacity, model, current_latitude, current_longitude, status
        FROM vehicles WHERE driver_id = ?
    ''', (session['user_id'],))

    vehicle = cursor.fetchone()
    conn.close()

    # Get additional students from parents.db
    parents_db_students = []
    try:
        parents_db_path = PROJECT_ROOT / "parents.db"
        if parents_db_path.exists():
            parents_conn = sqlite3.connect(parents_db_path)
            parents_cursor = parents_conn.cursor()
            
            parents_cursor.execute('''
                SELECT full_name, child_name, phone_number, address 
                FROM PARENTS 
                WHERE address IS NOT NULL AND address != ''
                ORDER BY child_name
            ''')
            
            parent_records = parents_cursor.fetchall()
            parents_conn.close()
            
            for i, (parent_name, child_name, phone, address) in enumerate(parent_records):
                parents_db_students.append({
                    'id': f'parent_db_{i}',
                    'name': child_name or f'Child of {parent_name}',
                    'class': f'Grade {(i % 5) + 1}',
                    'status': 'available',
                    'pickup_address': address,
                    'dropoff_address': 'School',  # Default dropoff
                    'parent_name': parent_name,
                    'parent_phone': phone or '0555 123 4567'
                })
    except Exception as e:
        print(f"Error loading parents.db data: {e}")

    # Combine students from both sources
    all_students = []
    
    # Add students from main database
    for student in main_db_students:
        all_students.append({
            'id': student[0],
            'name': student[1],
            'class': student[2],
            'status': student[3],
            'pickup_address': student[4],
            'dropoff_address': student[5],
            'parent_name': student[6],
            'parent_phone': student[7],
            'source': 'main_db'
        })
    
    # Add students from parents.db
    all_students.extend([{**s, 'source': 'parents_db'} for s in parents_db_students])

    # Vehicle info
    vehicle_info = {
        'id': vehicle[0] if vehicle else None,
        'plate': vehicle[1] if vehicle else 'No Vehicle Assigned',
        'capacity': vehicle[2] if vehicle else 0,
        'model': vehicle[3] if vehicle else 'N/A',
        'current_location': {
            'lat': vehicle[4], 
            'lng': vehicle[5]
        } if vehicle and vehicle[4] else {'lat': 39.9334, 'lng': 32.8597},  # Default Ankara center
        'status': vehicle[6] if vehicle else 'unknown'
    }

    # Get today's route history
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.event_type, a.timestamp, s.full_name as student_name, a.location
        FROM attendance_logs a
        JOIN students s ON a.student_id = s.id
        WHERE a.verified_by = ? AND DATE(a.timestamp) = DATE('now')
        ORDER BY a.timestamp DESC
    ''', (session['user_id'],))

    route_history = []
    for log in cursor.fetchall():
        route_history.append({
            'event_type': log[0],
            'timestamp': log[1],
            'student_name': log[2],
            'location': log[3]
        })
    conn.close()
    
    return render_template("driver-route.html",
                           user_name=session['full_name'],
                           vehicle=vehicle_info,
                           students=all_students,
                           route_history=route_history,
                           api_key="AIzaSyBnMCJBIa3Nld1h7SeIbPj1NV58FmAkZ_c",
                           current_user={
                               'id': session['user_id'],
                               'name': session['full_name'],
                               'role': session['user_role']
                           })


@app.route("/api/get-all-student-addresses")
@login_required
@role_required('driver')
def api_get_all_student_addresses():
    """Get all student addresses from both main DB and parents.db"""
    try:
        all_students = []
        
        # Get from main database
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.full_name, s.pickup_address, s.class_name, s.current_status,
                   p.full_name as parent_name, p.phone as parent_phone
            FROM students s
            LEFT JOIN users p ON s.parent_id = p.id
            WHERE s.assigned_driver_id = ? AND s.is_active = 1
            ORDER BY s.full_name
        ''', (session['user_id'],))
        
        main_students = cursor.fetchall()
        conn.close()
        
        for student in main_students:
            all_students.append({
                'id': student[0],
                'name': student[1],
                'address': student[2] or 'No address set',
                'class': student[3] or 'No class',
                'status': student[4] or 'unknown',
                'parent_name': student[5] or 'No parent',
                'parent_phone': student[6] or 'No phone',
                'source': 'main_db'
            })
        
        # Get from parents.db
        try:
            parents_db_path = PROJECT_ROOT / "parents.db"
            if parents_db_path.exists():
                parents_conn = sqlite3.connect(parents_db_path)
                parents_cursor = parents_conn.cursor()
                
                parents_cursor.execute('''
                    SELECT full_name, child_name, phone_number, address 
                    FROM PARENTS 
                    WHERE address IS NOT NULL AND address != ''
                    ORDER BY child_name
                ''')
                
                parent_records = parents_cursor.fetchall()
                parents_conn.close()
                
                for i, (parent_name, child_name, phone, address) in enumerate(parent_records):
                    all_students.append({
                        'id': f'parents_db_{i}',
                        'name': child_name or f'Child of {parent_name}',
                        'address': address,
                        'class': f'Grade {(i % 5) + 1}',
                        'status': 'available',
                        'parent_name': parent_name,
                        'parent_phone': phone or '0555 123 4567',
                        'source': 'parents_db'
                    })
        except Exception as e:
            print(f"Error loading parents.db: {e}")
        
        return jsonify({
            'success': True,
            'students': all_students,
            'total_count': len(all_students)
        })
        
    except Exception as e:
        print(f"Error getting all student addresses: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/plan-optimal-route", methods=['POST'])
@login_required
@role_required('driver')
def api_plan_optimal_route():
    """Plan optimal route using selected student addresses"""
    try:
        data = request.get_json()
        selected_students = data.get('selected_students', [])
        start_location = data.get('start_location', 'Ankara, Turkey')
        end_location = data.get('end_location', 'School, Ankara')
        
        if not selected_students:
            return jsonify({'success': False, 'error': 'No students selected'})
        
        # Get addresses for selected students
        addresses = []
        
        # Check both databases for student addresses
        for student_id in selected_students:
            address = None
            
            if student_id.startswith('parents_db_'):
                # Get from parents.db
                try:
                    parents_db_path = PROJECT_ROOT / "parents.db"
                    if parents_db_path.exists():
                        parents_conn = sqlite3.connect(parents_db_path)
                        parents_cursor = parents_conn.cursor()
                        
                        # Extract index from student_id (e.g., 'parents_db_0' -> 0)
                        index = int(student_id.split('_')[-1])
                        
                        parents_cursor.execute('''
                            SELECT address FROM PARENTS 
                            WHERE address IS NOT NULL AND address != ''
                            ORDER BY child_name
                            LIMIT 1 OFFSET ?
                        ''', (index,))
                        
                        result = parents_cursor.fetchone()
                        if result:
                            address = result[0]
                        parents_conn.close()
                except Exception as e:
                    print(f"Error getting address from parents.db: {e}")
            else:
                # Get from main database
                conn = sqlite3.connect(USERS_DB)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT pickup_address FROM students WHERE id = ?
                ''', (student_id,))
                result = cursor.fetchone()
                if result:
                    address = result[0]
                conn.close()
            
            if address:
                addresses.append(address)
        
        if not addresses:
            return jsonify({'success': False, 'error': 'No valid addresses found for selected students'})
        
        # Use your existing route planning logic
        waypoints_str = ','.join(addresses)
        
        # Try both Google and ORS APIs
        google_route = get_google_directions(start_location, end_location, addresses)
        ors_route = get_ors_directions(start_location, end_location, addresses)
        
        if not google_route and not ors_route:
            return jsonify({'success': False, 'error': 'Could not plan route with either API'})
        
        # Choose the best route
        best_route = None
        if google_route and ors_route:
            best_route = min([google_route, ors_route], key=lambda r: r["duration"])
        else:
            best_route = google_route or ors_route
        
        return jsonify({
            'success': True,
            'route': {
                'source': best_route['source'],
                'polyline': best_route['polyline'],
                'duration_seconds': best_route['duration'],
                'duration_minutes': round(best_route['duration'] / 60, 1),
                'waypoints': addresses,
                'total_stops': len(addresses) + 2  # start + waypoints + end
            }
        })
        
    except Exception as e:
        print(f"Error planning route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/save-route", methods=['POST'])
@login_required
@role_required('driver')
def api_save_route():
    """Save planned route to database"""
    try:
        data = request.get_json()
        route_data = data.get('route_data')
        selected_students = data.get('selected_students', [])
        
        if not route_data:
            return jsonify({'success': False, 'error': 'No route data provided'})
        
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        
        # Create routes table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS planned_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_id TEXT NOT NULL,
                route_name TEXT,
                polyline TEXT,
                waypoints TEXT,
                duration_minutes REAL,
                student_ids TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Save the route
        cursor.execute('''
            INSERT INTO planned_routes 
            (driver_id, route_name, polyline, waypoints, duration_minutes, student_ids)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'],
            f"Route {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            route_data.get('polyline', ''),
            ','.join(route_data.get('waypoints', [])),
            route_data.get('duration_minutes', 0),
            ','.join(selected_students)
        ))
        
        route_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Route saved successfully',
            'route_id': route_id
        })
        
    except Exception as e:
        print(f"Error saving route: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/get-saved-routes")
@login_required
@role_required('driver')
def api_get_saved_routes():
    """Get all saved routes for current driver"""
    try:
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='planned_routes'
        ''')
        
        if not cursor.fetchone():
            return jsonify({'success': True, 'routes': []})
        
        cursor.execute('''
            SELECT id, route_name, waypoints, duration_minutes, student_ids, created_at
            FROM planned_routes
            WHERE driver_id = ? AND is_active = 1
            ORDER BY created_at DESC
        ''', (session['user_id'],))
        
        routes = []
        for route in cursor.fetchall():
            routes.append({
                'id': route[0],
                'name': route[1],
                'waypoints': route[2].split(',') if route[2] else [],
                'duration_minutes': route[3],
                'student_count': len(route[4].split(',')) if route[4] else 0,
                'created_at': route[5]
            })
        
        conn.close()
        return jsonify({'success': True, 'routes': routes})
        
    except Exception as e:
        print(f"Error getting saved routes: {e}")
        return jsonify({'success': False, 'error': str(e)})










# Add this new route to your main.py file

@app.route("/api/students")
@login_required
@role_required('driver')
def get_students():
    """Get students assigned to the current driver"""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.id, s.full_name, s.pickup_address, s.dropoff_address, s.class_name
        FROM students s
        WHERE s.assigned_driver_id = ? AND s.is_active = 1
        ORDER BY s.full_name
    ''', (session['user_id'],))
    
    students = []
    for student in cursor.fetchall():
        students.append({
            'id': student[0],
            'name': student[1],
            'pickup_address': student[2],
            'dropoff_address': student[3],
            'class_name': student[4]
        })
    
    conn.close()
    return jsonify(students)

# Also add a route to get all unique addresses for autocomplete
@app.route("/api/addresses")
@login_required
@role_required('driver')
def get_addresses():
    """Get all unique addresses for autocomplete"""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT pickup_address FROM students 
        WHERE assigned_driver_id = ? AND is_active = 1 AND pickup_address IS NOT NULL
        UNION
        SELECT DISTINCT dropoff_address FROM students 
        WHERE assigned_driver_id = ? AND is_active = 1 AND dropoff_address IS NOT NULL
        ORDER BY pickup_address
    ''', (session['user_id'], session['user_id']))
    
    addresses = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()
    return jsonify(addresses)

# Add the route API endpoint to your main.py
@app.route("/api/route")
@login_required
@role_required('driver')
def get_best_route():
    """Simple route API - based on your working version"""
    origin = request.args.get("origin")
    destination = request.args.get("destination")
    waypoints = request.args.get("waypoints")
    
    if not origin or not destination:
        return jsonify({"error": "Missing origin or destination"}), 400
    
    # Parse waypoints - keep it simple
    waypoints_list = []
    if waypoints:
        waypoints_list = [w.strip() for w in waypoints.split(",") if w.strip()]
    
    print(f"Route request - Origin: {origin}, Destination: {destination}, Waypoints: {waypoints_list}")
    
    # Try both APIs
    google_route = get_google_directions(origin, destination, waypoints_list)
    ors_route = get_ors_directions(origin, destination, waypoints_list)
    
    # Return the best route or error
    if not google_route and not ors_route:
        return jsonify({"error": "No route found from either API"}), 500
    
    # Choose the best route (shortest duration)
    best_route = min(
        [r for r in [google_route, ors_route] if r],
        key=lambda r: r["duration"]
    )
    
    return jsonify({
        "source": best_route["source"],
        "polyline": best_route["polyline"],
        "duration_seconds": best_route["duration"],
        "duration_minutes": round(best_route["duration"] / 60, 1)
    })







# Replace the student API routes in your main.py with these enhanced versions:

# Replace the student API routes in your main.py with these enhanced versions:

# Replace the student API routes in your main.py with these enhanced versions:

@app.route("/api/get-student-addresses")
@login_required
@role_required('driver')
def api_get_student_addresses():
    """Get all student pickup addresses for the current driver with debugging"""
    try:
        print(f"🔍 Getting student addresses for driver: {session.get('user_id')} ({session.get('full_name')})")

        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()

        # First, let's check if we have any students at all
        cursor.execute('SELECT COUNT(*) FROM students WHERE is_active = 1')
        total_students = cursor.fetchone()[0]
        print(f"📊 Total active students in database: {total_students}")

        # Check if this driver has any assigned students
        cursor.execute('''
            SELECT COUNT(*) FROM students 
            WHERE assigned_driver_id = ? AND is_active = 1
        ''', (session['user_id'],))
        assigned_count = cursor.fetchone()[0]
        print(f"📊 Students assigned to this driver: {assigned_count}")

        # Get assigned students with their pickup addresses
        cursor.execute('''
            SELECT s.id, s.full_name, s.pickup_address, s.class_name, s.current_status,
                   p.full_name as parent_name, p.phone as parent_phone
            FROM students s
            LEFT JOIN users p ON s.parent_id = p.id
            WHERE s.assigned_driver_id = ? AND s.is_active = 1
            ORDER BY s.full_name
        ''', (session['user_id'],))

        students = []
        for student in cursor.fetchall():
            print(f"📝 Found student: {student[1]} at {student[2]}")
            students.append({
                'id': student[0],
                'name': student[1],
                'address': student[2] or 'No address set',  # Handle null addresses
                'class': student[3] or 'No class',
                'status': student[4] or 'unknown',
                'parent_name': student[5] or 'No parent',
                'parent_phone': student[6] or 'No phone'
            })

        conn.close()

        print(f"✅ Returning {len(students)} students")
        return jsonify({
            'success': True,
            'students': students,
            'debug_info': {
                'total_students': total_students,
                'assigned_to_driver': assigned_count,
                'driver_id': session['user_id'],
                'driver_name': session['full_name']
            }
        })

    except Exception as e:
        print(f"❌ Error getting student addresses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/get-parent-addresses")
@login_required
@role_required('driver')
def api_get_parent_addresses():
    """Get addresses from parents.db SQLite database"""
    try:
        print("🔍 Trying to get parent addresses from parents.db SQLite database")

        # Connect to parents.db SQLite database
        parents_db_path = PROJECT_ROOT / "parents.db"

        if not parents_db_path.exists():
            print(f"❌ Parents database not found at: {parents_db_path}")
            return jsonify({'success': False, 'error': 'Parents database not found'})

        print(f"📁 Found parents database at: {parents_db_path}")

        # Connect to the parents database
        conn = sqlite3.connect(parents_db_path)
        cursor = conn.cursor()

        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📊 Tables in parents.db: {tables}")

        # Get column information for PARENTS table
        cursor.execute("PRAGMA table_info(PARENTS)")
        columns = cursor.fetchall()
        print(f"📊 Columns in PARENTS table: {columns}")

        # Get column names
        column_names = [col[1] for col in columns]
        print(f"📊 Column names: {column_names}")

        # Try different possible column name variations
        possible_address_columns = ['address', 'Address', 'ADDRESS', 'full_address', 'location']
        possible_name_columns = ['child_name', 'child_nam', 'full_name', 'name']
        possible_phone_columns = ['phone_number', 'phone_num', 'phone', 'Phone']

        # Find the correct column names
        address_col = None
        name_col = None
        phone_col = None

        for col in possible_address_columns:
            if col in column_names:
                address_col = col
                break

        for col in possible_name_columns:
            if col in column_names:
                name_col = col
                break

        for col in possible_phone_columns:
            if col in column_names:
                phone_col = col
                break

        print(f"🎯 Using columns - Address: {address_col}, Name: {name_col}, Phone: {phone_col}")

        # Build the query dynamically
        if not address_col:
            # If no address column found, use all columns and see what we have
            cursor.execute("SELECT * FROM PARENTS LIMIT 1")
            sample_row = cursor.fetchone()
            print(f"📄 Sample row data: {sample_row}")
            return jsonify({'success': False, 'error': f'Address column not found. Available columns: {column_names}'})

        # Build the SELECT query
        select_query = f"SELECT "
        select_fields = []

        if 'full_name' in column_names:
            select_fields.append('full_name')
        else:
            select_fields.append(column_names[0])  # Use first column as fallback

        if name_col:
            select_fields.append(name_col)
        else:
            select_fields.append("'' as child_name")

        if phone_col:
            select_fields.append(phone_col)
        else:
            select_fields.append("'' as phone")

        select_fields.append(address_col)

        select_query += ", ".join(select_fields) + " FROM PARENTS"

        print(f"📝 Executing query: {select_query}")
        cursor.execute(select_query)
        parent_records = cursor.fetchall()

        print(f"📊 Found {len(parent_records)} parent records")

        addresses = []
        for i, record in enumerate(parent_records):
            print(f"📝 Raw record {i + 1}: {record}")

            if len(record) >= 4:
                full_name = record[0] or f"Parent {i + 1}"
                child_name = record[1] or f"Child {i + 1}"
                phone_number = record[2] or f"0555 000 00{i + 10:02d}"
                address = record[3] or f"Address not available for {full_name}"

                print(
                    f"📝 Processed {i + 1}: Parent: {full_name} | Child: {child_name} | Phone: {phone_number} | Address: {address}")

                addresses.append({
                    'id': f"parent_{i}",
                    'name': child_name,  # Use child_name as student name
                    'parent_name': full_name,
                    'phone': phone_number,
                    'address': address,
                    'class': f"Grade {(i % 5) + 1}",  # Random grade assignment
                    'status': 'available'
                })
            else:
                print(f"⚠️ Record {i + 1} has insufficient data: {record}")

        conn.close()

        print(f"✅ Returning {len(addresses)} parent addresses")
        return jsonify({'success': True, 'addresses': addresses})

    except Exception as e:
        print(f"❌ Error getting parent addresses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/debug-parents-table")
@login_required
def api_debug_parents_table():
    """Debug endpoint to inspect the exact structure of the PARENTS table"""
    try:
        parents_db_path = PROJECT_ROOT / "parents.db"

        if not parents_db_path.exists():
            return jsonify({'success': False, 'error': 'Parents database not found'})

        conn = sqlite3.connect(parents_db_path)
        cursor = conn.cursor()

        # Get table structure
        cursor.execute("PRAGMA table_info(PARENTS)")
        columns = cursor.fetchall()

        # Get all data
        cursor.execute("SELECT * FROM PARENTS")
        all_records = cursor.fetchall()

        # Get first few records for inspection
        cursor.execute("SELECT * FROM PARENTS LIMIT 3")
        sample_records = cursor.fetchall()

        conn.close()

        return jsonify({
            'success': True,
            'columns': columns,
            'total_records': len(all_records),
            'sample_records': sample_records,
            'column_names': [col[1] for col in columns]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/create-sample-students")
@login_required
@role_required('driver')
def api_create_sample_students():
    """Create sample students from parents.db data"""
    try:
        print("🔧 Creating students from parents.db data...")

        # First get data from parents.db
        parents_db_path = PROJECT_ROOT / "parents.db"

        if not parents_db_path.exists():
            return jsonify({'success': False, 'error': 'Parents database not found'})

        # Connect to parents database
        parents_conn = sqlite3.connect(parents_db_path)
        parents_cursor = parents_conn.cursor()

        parents_cursor.execute("SELECT full_name, child_name, phone_number, address FROM PARENTS")
        parent_records = parents_cursor.fetchall()
        parents_conn.close()

        if not parent_records:
            return jsonify({'success': False, 'error': 'No parent data found'})

        # Connect to main database
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()

        # Check if we already have students
        cursor.execute('SELECT COUNT(*) FROM students')
        existing_count = cursor.fetchone()[0]

        # Get current driver ID
        driver_id = session['user_id']

        # Create students from parent data
        created_count = 0
        for i, (parent_name, child_name, phone, address) in enumerate(parent_records):
            student_id = f"STU2024{i + 1:03d}"
            student_name = child_name or f"Child of {parent_name}"
            class_name = f"{(i % 5) + 1}-{chr(65 + (i % 3))}"  # Random class like "1-A", "2-B", etc.

            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO students 
                    (student_id, full_name, class_name, pickup_address, assigned_driver_id, 
                     is_active, current_status, emergency_contact)
                    VALUES (?, ?, ?, ?, ?, 1, 'at_home', ?)
                ''', (student_id, student_name, class_name, address, driver_id, phone))

                if cursor.rowcount > 0:
                    created_count += 1
                    print(f"✅ Created student: {student_name} at {address}")

            except Exception as e:
                print(f"⚠️ Error creating student {student_name}: {e}")
                continue

        conn.commit()
        conn.close()

        print(f"✅ Created {created_count} students from parent data")
        return jsonify({
            'success': True,
            'message': f'Created {created_count} students from parent database',
            'total_parents': len(parent_records),
            'existing_students': existing_count,
            'new_students': created_count
        })

    except Exception as e:
        print(f"❌ Error creating students from parent data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/debug-databases")
@login_required
def api_debug_databases():
    """Debug endpoint to check database contents"""
    try:
        debug_info = {}

        # Check main database
        try:
            conn = sqlite3.connect(USERS_DB)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM students')
            debug_info['main_db_students'] = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM users WHERE role = "driver"')
            debug_info['main_db_drivers'] = cursor.fetchone()[0]

            cursor.execute('SELECT id, full_name, role FROM users WHERE role = "driver"')
            debug_info['drivers'] = cursor.fetchall()

            conn.close()
        except Exception as e:
            debug_info['main_db_error'] = str(e)

        # Check parents database
        try:
            parents_db_path = PROJECT_ROOT / "parents.db"
            if parents_db_path.exists():
                conn = sqlite3.connect(parents_db_path)
                cursor = conn.cursor()

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                debug_info['parents_db_tables'] = cursor.fetchall()

                cursor.execute("SELECT COUNT(*) FROM PARENTS")
                debug_info['parents_db_count'] = cursor.fetchone()[0]

                cursor.execute("SELECT full_name, child_name, address FROM PARENTS LIMIT 3")
                debug_info['parents_db_sample'] = cursor.fetchall()

                conn.close()
            else:
                debug_info['parents_db_error'] = 'File not found'
        except Exception as e:
            debug_info['parents_db_error'] = str(e)

        return jsonify({'success': True, 'debug_info': debug_info})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# Add these routes to your main.py to help update addresses in the parents.db

@app.route("/api/update-parent-address", methods=["POST"])
@login_required
@role_required('admin')  # Only admin can update addresses
def api_update_parent_address():
    """Update address for a specific parent in parents.db"""
    try:
        data = request.get_json()
        parent_id = data.get('parent_id')  # Like "Parent1"
        new_address = data.get('address')

        if not parent_id or not new_address:
            return jsonify({'success': False, 'error': 'Missing parent_id or address'})

        parents_db_path = PROJECT_ROOT / "parents.db"

        if not parents_db_path.exists():
            return jsonify({'success': False, 'error': 'Parents database not found'})

        # Check if file is writable
        if not os.access(parents_db_path, os.W_OK):
            return jsonify({'success': False, 'error': 'Database file is read-only'})

        conn = sqlite3.connect(parents_db_path)
        cursor = conn.cursor()

        # Update the address - assuming full_name contains "Parent1", "Parent2", etc.
        cursor.execute('''
            UPDATE PARENTS 
            SET address = ? 
            WHERE full_name = ?
        ''', (new_address, parent_id))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected > 0:
            print(f"✅ Updated address for {parent_id}: {new_address}")
            return jsonify({'success': True, 'message': f'Updated address for {parent_id}'})
        else:
            return jsonify({'success': False, 'error': f'No parent found with ID {parent_id}'})

    except Exception as e:
        print(f"❌ Error updating address: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/fix-all-addresses", methods=["POST"])
@login_required
@role_required('admin')
def api_fix_all_addresses():
    """Fix all null addresses in parents.db with the correct addresses"""
    try:
        parents_db_path = PROJECT_ROOT / "parents.db"

        if not parents_db_path.exists():
            return jsonify({'success': False, 'error': 'Parents database not found'})

        # Check if file is writable
        if not os.access(parents_db_path, os.W_OK):
            return jsonify({'success': False, 'error': 'Database file is read-only. Please check file permissions.'})

        conn = sqlite3.connect(parents_db_path)
        cursor = conn.cursor()

        # The correct addresses from your original data
        correct_addresses = {
            'Parent1': 'Tunali Hilmi Caddesi No: 45/8, Cankaya, Ankara',
            'Parent2': 'Bulten Sokak No: 12/3, Cankaya, Ankara',
            'Parent3': 'Kizilirmak Sokak No: 28/5, Cankaya, Ankara',
            'Parent4': 'Arjantin Caddesi No: 67/11, Cankaya, Ankara'
        }

        updated_count = 0

        for parent_id, address in correct_addresses.items():
            cursor.execute('''
                UPDATE PARENTS 
                SET address = ? 
                WHERE full_name = ?
            ''', (address, parent_id))

            if cursor.rowcount > 0:
                updated_count += 1
                print(f"✅ Updated {parent_id}: {address}")
            else:
                print(f"⚠️ No record found for {parent_id}")

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} addresses',
            'updated_count': updated_count,
            'total_attempted': len(correct_addresses)
        })

    except Exception as e:
        print(f"❌ Error fixing addresses: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/check-db-permissions")
@login_required
def api_check_db_permissions():
    """Check database file permissions and provide troubleshooting info"""
    try:
        parents_db_path = PROJECT_ROOT / "parents.db"

        info = {
            'file_exists': parents_db_path.exists(),
            'file_path': str(parents_db_path),
            'current_dir': str(PROJECT_ROOT)
        }

        if parents_db_path.exists():
            import stat
            file_stat = parents_db_path.stat()

            info.update({
                'readable': os.access(parents_db_path, os.R_OK),
                'writable': os.access(parents_db_path, os.W_OK),
                'file_size': file_stat.st_size,
                'permissions': oct(file_stat.st_mode)[-3:],
                'owner_writable': bool(file_stat.st_mode & stat.S_IWUSR),
                'group_writable': bool(file_stat.st_mode & stat.S_IWGRP),
                'other_writable': bool(file_stat.st_mode & stat.S_IWOTH)
            })

            # Try to test write access
            try:
                conn = sqlite3.connect(parents_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM PARENTS")
                record_count = cursor.fetchone()[0]
                conn.close()
                info['can_read_db'] = True
                info['record_count'] = record_count
            except Exception as e:
                info['can_read_db'] = False
                info['read_error'] = str(e)

            # Try a test write
            try:
                conn = sqlite3.connect(parents_db_path)
                cursor = conn.cursor()
                # Just test if we can begin a transaction
                cursor.execute("BEGIN TRANSACTION")
                cursor.execute("ROLLBACK")
                conn.close()
                info['can_write_db'] = True
            except Exception as e:
                info['can_write_db'] = False
                info['write_error'] = str(e)

        return jsonify({'success': True, 'info': info})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/recreate-parents-db")
@login_required
@role_required('admin')
def api_recreate_parents_db():
    """Recreate the parents database with correct data"""
    try:
        parents_db_path = PROJECT_ROOT / "parents.db"
        backup_path = PROJECT_ROOT / f"parents_backup_{int(time.time())}.db"

        # Backup existing database
        if parents_db_path.exists():
            import shutil
            shutil.copy2(parents_db_path, backup_path)
            print(f"📦 Backed up existing database to: {backup_path}")

        # Create new database
        conn = sqlite3.connect(parents_db_path)
        cursor = conn.cursor()

        # Create table with correct structure
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS PARENTS (
                full_name TEXT PRIMARY KEY,
                child_name TEXT,
                phone_number TEXT,
                address TEXT
            )
        ''')

        # Insert the correct data
        parent_data = [
            ('Parent1', 'Egemen Doruk Serdar', '0543 345 89 33', 'Tunali Hilmi Caddesi No: 45/8, Cankaya, Ankara'),
            ('Parent2', 'Mustafa Pinarci', '0597 398 23 23', 'Bulten Sokak No: 12/3, Cankaya, Ankara'),
            ('Parent3', 'Ege Izmir', '0567 897 67 21', 'Kizilirmak Sokak No: 28/5, Cankaya, Ankara'),
            ('Parent4', 'Mustafa Bogac Morkoyun', '0547 323 89 92', 'Arjantin Caddesi No: 67/11, Cankaya, Ankara')
        ]

        # Clear existing data and insert new
        cursor.execute('DELETE FROM PARENTS')
        cursor.executemany('''
            INSERT INTO PARENTS (full_name, child_name, phone_number, address)
            VALUES (?, ?, ?, ?)
        ''', parent_data)

        conn.commit()
        conn.close()

        print("✅ Recreated parents database with correct addresses")

        return jsonify({
            'success': True,
            'message': 'Database recreated successfully',
            'backup_created': str(backup_path),
            'records_inserted': len(parent_data)
        })

    except Exception as e:
        print(f"❌ Error recreating database: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})









# ==================== ADMIN ROUTES ====================

@app.route("/admin")
@login_required
@role_required('admin')
def admin_dashboard():
    """Enhanced admin dashboard with real statistics"""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()

    # Real statistics
    cursor.execute('SELECT COUNT(*) FROM students WHERE is_active = 1')
    total_students = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "parent" AND is_active = 1')
    total_parents = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "driver" AND is_active = 1')
    total_drivers = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM vehicles WHERE is_active = 1')
    total_vehicles = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM attendance_logs 
        WHERE DATE(timestamp) = DATE('now') AND event_type = 'board'
    ''')
    today_attendance = cursor.fetchone()[0]

    # Calculate attendance rate
    attendance_rate = (today_attendance / total_students * 100) if total_students > 0 else 0

    # Get active vehicles with location
    cursor.execute('''
        SELECT v.id, v.license_plate, v.current_latitude, v.current_longitude, 
               v.status, u.full_name as driver_name
        FROM vehicles v
        JOIN users u ON v.driver_id = u.id
        WHERE v.is_active = 1
    ''')

    active_vehicles = []
    for vehicle in cursor.fetchall():
        active_vehicles.append({
            'id': vehicle[0],
            'plate': vehicle[1],
            'location': {'lat': vehicle[2], 'lng': vehicle[3]} if vehicle[2] else None,
            'status': vehicle[4],
            'driver': vehicle[5]
        })

    # Get recent activities
    cursor.execute('''
        SELECT a.event_type, a.timestamp, s.full_name as student_name,
               u.full_name as driver_name
        FROM attendance_logs a
        JOIN students s ON a.student_id = s.id
        JOIN users u ON a.verified_by = u.id
        ORDER BY a.timestamp DESC
        LIMIT 10
    ''')

    recent_activities = []
    for activity in cursor.fetchall():
        recent_activities.append({
            'type': activity[0],
            'time': activity[1],
            'student': activity[2],
            'driver': activity[3]
        })

    stats = {
        'total_students': total_students,
        'total_parents': total_parents,
        'total_drivers': total_drivers,
        'total_vehicles': total_vehicles,
        'today_attendance': today_attendance,
        'attendance_rate': round(attendance_rate, 1),
        'active_vehicles': active_vehicles,
        'recent_activities': recent_activities
    }

    conn.close()
    return render_template("admin.html",
                           user_name=session['full_name'],
                           stats=stats,
                           current_user={
                               'id': session['user_id'],
                               'name': session['full_name'],
                               'role': session['user_role']
                           })


# ==================== UNIFIED MESSAGING ROUTES ====================

@app.route("/messages")
@login_required
def unified_messages():
    """Unified messaging interface for all user roles"""
    return render_template("messages.html",
                           current_user={
                               'id': session['user_id'],
                               'name': session['full_name'],
                               'role': session['user_role']
                           })


@app.route("/api/get-contacts")
@login_required
def api_get_contacts():
    """Get contacts based on user role"""
    try:
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()

        contacts = []
        user_role = session['user_role']
        user_id = session['user_id']

        if user_role == 'parent':
            # Parents can message drivers of their children's vehicles
            cursor.execute('''
                SELECT DISTINCT u.id, u.full_name, u.phone, u.online_status, v.license_plate,
                       s.full_name as student_name, u.role
                FROM users u
                JOIN students s ON u.id = s.assigned_driver_id
                LEFT JOIN vehicles v ON u.id = v.driver_id
                WHERE s.parent_id = ? AND u.is_active = 1
            ''', (user_id,))

            for row in cursor.fetchall():
                contacts.append({
                    'id': row[0],
                    'name': row[1],
                    'phone': row[2],
                    'status': row[3] or 'offline',
                    'vehicle': row[4],
                    'student': row[5],
                    'role': row[6],
                    'unread_count': get_unread_count(user_id, row[0]),
                    'last_message': get_last_message(user_id, row[0]),
                    'last_message_time': get_last_message_time(user_id, row[0])
                })

        elif user_role == 'driver':
            # Drivers can message parents of their assigned students
            cursor.execute('''
                SELECT DISTINCT u.id, u.full_name, u.phone, u.online_status, 
                       s.full_name as student_name, u.role
                FROM users u
                JOIN students s ON u.id = s.parent_id
                WHERE s.assigned_driver_id = ? AND u.is_active = 1
            ''', (user_id,))

            for row in cursor.fetchall():
                contacts.append({
                    'id': row[0],
                    'name': row[1],
                    'phone': row[2],
                    'status': row[3] or 'offline',
                    'student': row[4],
                    'role': row[5],
                    'unread_count': get_unread_count(user_id, row[0]),
                    'last_message': get_last_message(user_id, row[0]),
                    'last_message_time': get_last_message_time(user_id, row[0])
                })

        elif user_role == 'admin':
            # Admins can message everyone except themselves
            cursor.execute('''
                SELECT u.id, u.full_name, u.phone, u.online_status, u.role
                FROM users u
                WHERE u.id != ? AND u.is_active = 1
                ORDER BY u.role, u.full_name
            ''', (user_id,))

            for row in cursor.fetchall():
                contacts.append({
                    'id': row[0],
                    'name': row[1],
                    'phone': row[2],
                    'status': row[3] or 'offline',
                    'role': row[4],
                    'unread_count': get_unread_count(user_id, row[0]),
                    'last_message': get_last_message(user_id, row[0]),
                    'last_message_time': get_last_message_time(user_id, row[0])
                })

        conn.close()
        return jsonify({'contacts': contacts})

    except Exception as e:
        print(f"❌ Error getting contacts: {e}")
        return jsonify({'contacts': []})


def get_unread_count(user_id, contact_id):
    """Get unread message count between two users"""
    try:
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
        ''', (contact_id, user_id))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0


def get_last_message(user_id, contact_id):
    """Get last message between two users"""
    try:
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT message_text FROM messages 
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY sent_at DESC LIMIT 1
        ''', (user_id, contact_id, contact_id, user_id))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None


def get_last_message_time(user_id, contact_id):
    """Get last message time between two users"""
    try:
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sent_at FROM messages 
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY sent_at DESC LIMIT 1
        ''', (user_id, contact_id, contact_id, user_id))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None


# Update the existing get_messages API to include sender role
@app.route("/api/get-messages/<int:contact_id>")
@login_required
def api_get_messages(contact_id):
    """Get real message history with sender roles"""
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT m.id, m.message_text, m.sent_at, m.is_read,
               sender.full_name as sender_name, sender.id as sender_id, sender.role as sender_role
        FROM messages m
        JOIN users sender ON m.sender_id = sender.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.sent_at ASC
        LIMIT 50
    ''', (session['user_id'], contact_id, contact_id, session['user_id']))

    messages = []
    for row in cursor.fetchall():
        messages.append({
            'id': row[0],
            'text': row[1],
            'sent_at': row[2],
            'is_read': row[3],
            'sender_name': row[4],
            'sender_id': row[5],
            'sender_role': row[6],
            'is_own': row[5] == session['user_id']
        })

    # Mark messages as read
    cursor.execute('''
        UPDATE messages SET is_read = 1, read_at = ?
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    ''', (datetime.now(), contact_id, session['user_id']))

    conn.commit()
    conn.close()
    return jsonify({'messages': messages})


# ==================== REAL-TIME API ROUTES ====================

@app.route("/api/send-message", methods=["POST"])
@login_required
def api_send_message():
    """Real-time message sending"""
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    message_text = data.get('message_text')

    if not receiver_id or not message_text:
        return jsonify({'success': False, 'error': 'Missing data'})

    message_id = messaging_service.send_message(
        session['user_id'],
        receiver_id,
        message_text
    )

    if message_id:
        return jsonify({'success': True, 'message_id': message_id})
    else:
        return jsonify({'success': False, 'error': 'Failed to send message'})


@app.route("/api/update-student-status", methods=["POST"])
@login_required
@role_required('driver')
def api_update_student_status():
    """Update student attendance status"""
    data = request.get_json()
    student_id = data.get('student_id')
    event_type = data.get('event_type')  # 'board' or 'alight'

    success = attendance_service.log_attendance(
        student_id,
        event_type,
        session['user_id']
    )

    if success:
        # Update student current status
        status_map = {
            'board': 'on_bus',
            'alight': 'at_school' if datetime.now().hour < 15 else 'at_home'
        }

        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE students SET current_status = ? WHERE id = ?
        ''', (status_map.get(event_type, 'unknown'), student_id))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to log attendance'})


@app.route("/api/get-vehicle-location/<int:vehicle_id>")
@login_required
def api_get_vehicle_location(vehicle_id):
    """Get real-time vehicle location"""
    location = location_service.get_vehicle_location(vehicle_id)

    if location:
        return jsonify({
            'success': True,
            'location': location
        })
    else:
        # Fallback to database
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT current_latitude, current_longitude, last_location_update
            FROM vehicles WHERE id = ?
        ''', (vehicle_id,))

        result = cursor.fetchone()
        conn.close()

        if result and result[0] and result[1]:
            return jsonify({
                'success': True,
                'location': {
                    'latitude': result[0],
                    'longitude': result[1],
                    'last_update': result[2]
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Location not available'})


# ==================== SOCKETIO EVENTS ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if 'user_id' in session:
        join_room(f'user_{session["user_id"]}')
        join_room('location_tracking')

        print(f"✅ User {session['full_name']} connected")

        # Emit connection status to user
        emit('connection_status', {
            'status': 'connected',
            'user_id': session['user_id'],
            'timestamp': datetime.now().isoformat()
        })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if 'user_id' in session:
        leave_room(f'user_{session["user_id"]}')
        leave_room('location_tracking')
        print(f"❌ User {session.get('full_name', 'Unknown')} disconnected")


@socketio.on('join_chat')
def handle_join_chat(data):
    """Join a specific chat room"""
    contact_id = data.get('contact_id')
    if contact_id:
        room = f'chat_{min(session["user_id"], contact_id)}_{max(session["user_id"], contact_id)}'
        join_room(room)
        emit('joined_chat', {'room': room, 'contact_id': contact_id})


@socketio.on('send_message')
def handle_send_message(data):
    """Handle real-time message sending"""
    receiver_id = data.get('receiver_id')
    message_text = data.get('message_text')

    if receiver_id and message_text:
        message_id = messaging_service.send_message(
            session['user_id'],
            receiver_id,
            message_text
        )

        if message_id:
            emit('message_delivered', {
                'message_id': message_id,
                'status': 'delivered'
            })


@socketio.on('request_location')
def handle_location_request(data):
    """Handle location request"""
    vehicle_id = data.get('vehicle_id')
    if vehicle_id:
        location = location_service.get_vehicle_location(vehicle_id)

        emit('location_response', {
            'vehicle_id': vehicle_id,
            'location': location,
            'timestamp': datetime.now().isoformat()
        })


@socketio.on('typing_start')
def handle_typing_start(data):
    """Handle typing start event"""
    if 'user_id' in session:
        contact_id = data.get('contact_id')
        if contact_id:
            socketio.emit('user_typing', {
                'user_id': session['user_id'],
                'user_name': session['full_name'],
                'typing': True
            }, room=f'user_{contact_id}')


@socketio.on('typing_stop')
def handle_typing_stop(data):
    """Handle typing stop event"""
    if 'user_id' in session:
        contact_id = data.get('contact_id')
        if contact_id:
            socketio.emit('user_typing', {
                'user_id': session['user_id'],
                'user_name': session['full_name'],
                'typing': False
            }, room=f'user_{contact_id}')


@socketio.on('driver_status_update')
def handle_driver_status(data):
    """Handle driver status updates"""
    if session.get('user_role') == 'driver':
        status = data.get('status')  # 'driving', 'stopped', 'loading', etc.

        # Update database
        conn = sqlite3.connect(USERS_DB)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE vehicles SET status = ? WHERE driver_id = ?
        ''', (status, session['user_id']))
        conn.commit()
        conn.close()

        # Broadcast to parents of students
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT s.parent_id
            FROM students s
            WHERE s.assigned_driver_id = ?
        ''', (session['user_id'],))

        parent_ids = [row[0] for row in cursor.fetchall()]

        for parent_id in parent_ids:
            socketio.emit('driver_status_changed', {
                'driver_name': session['full_name'],
                'status': status,
                'timestamp': datetime.now().isoformat()
            }, room=f'user_{parent_id}')


# ==================== EMERGENCY SYSTEM ====================

@app.route("/api/emergency-alert", methods=["POST"])
@login_required
def api_emergency_alert():
    """Handle emergency alerts"""
    data = request.get_json()
    emergency_type = data.get('type')  # 'medical', 'accident', 'behavior', 'technical'
    message = data.get('message', '')
    location = data.get('location', {})

    # Log emergency
    print(f"🚨 EMERGENCY ALERT: {emergency_type} from {session['full_name']}")

    # Notify all admins immediately
    conn = sqlite3.connect(USERS_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE role = "admin" AND is_active = 1')
    admin_ids = [row[0] for row in cursor.fetchall()]

    emergency_message = f"ACİL DURUM: {session['full_name']} tarafından {emergency_type} bildirimi"

    for admin_id in admin_ids:
        # Create notification in database
        cursor.execute('''
            INSERT INTO notifications (user_id, title, message, notification_type)
            VALUES (?, ?, ?, ?)
        ''', (admin_id, "🚨 ACİL DURUM", emergency_message + f" - {message}", 'urgent'))

        # Send real-time notification
        socketio.emit('new_notification', {
            'title': "🚨 ACİL DURUM",
            'message': emergency_message + f" - {message}",
            'type': 'urgent',
            'timestamp': datetime.now().isoformat()
        }, room=f'user_{admin_id}')

    # If it's a driver emergency, notify parents of their students
    if session.get('user_role') == 'driver':
        cursor.execute('''
            SELECT DISTINCT s.parent_id, p.full_name
            FROM students s
            JOIN users p ON s.parent_id = p.id
            WHERE s.assigned_driver_id = ?
        ''', (session['user_id'],))

        for parent_id, parent_name in cursor.fetchall():
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message, notification_type)
                VALUES (?, ?, ?, ?)
            ''', (parent_id, "Şoförden Acil Bildirim", f"Çocuğunuzun şoförü acil durum bildirdi: {message}", 'urgent'))

            socketio.emit('new_notification', {
                'title': "Şoförden Acil Bildirim",
                'message': f"Çocuğunuzun şoförü acil durum bildirdi: {message}",
                'type': 'urgent',
                'timestamp': datetime.now().isoformat()
            }, room=f'user_{parent_id}')

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Emergency alert sent'})


@app.route("/api/student-status")
@login_required
@role_required('parent')
def api_student_status():
    """API endpoint to get current student status dynamically"""
    try:
        conn = sqlite3.connect(STUDENTS_DB)
        cursor = conn.cursor()

        parent_full_name = session['full_name']
        
        # Find student whose father_name or mother_name matches the logged-in parent's full_name
        cursor.execute('''
            SELECT full_name, class, gender, attendance
            FROM STUDENT 
            WHERE father_name = ? OR mother_name = ?
        ''', (parent_full_name, parent_full_name))

        student_data = cursor.fetchone()
        conn.close()

        if student_data:
            # Determine status based on attendance
            if student_data[3]:  # attendance is True
                status_text = 'In the bus'
                status_class = 'status-on-bus'
                status_icon = '🚌'
            else:  # attendance is False
                status_text = 'At Home'
                status_class = 'status-at-home'
                status_icon = '🏠'
            
            return jsonify({
                'success': True,
                'student': {
                    'name': student_data[0],
                    'class': student_data[1],
                    'gender': student_data[2],
                    'attendance': student_data[3],
                    'status': status_text,
                    'status_class': status_class,
                    'status_icon': status_icon
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route("/api/save-activity", methods=["POST"])
@login_required
@role_required('parent')
def api_save_activity():
    """Save a new activity to the database"""
    try:
        data = request.get_json()
        student_name = data.get('student_name')
        activity_type = data.get('activity_type')
        activity_text = data.get('activity_text')
        
        conn = sqlite3.connect(STUDENTS_DB)
        cursor = conn.cursor()
        
        # Create activities table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ACTIVITIES (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_name TEXT NOT NULL,
                student_name TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                activity_text TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert new activity with Turkey timezone (UTC+3)
        from datetime import timezone
        turkey_tz = timezone(timedelta(hours=3))
        turkey_time = datetime.now(turkey_tz)
        cursor.execute('''
            INSERT INTO ACTIVITIES (parent_name, student_name, activity_type, activity_text, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['full_name'], student_name, activity_type, activity_text, turkey_time.strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/get-activities")
@login_required
@role_required('parent')
def api_get_activities():
    """Get activities for the logged-in parent"""
    try:
        conn = sqlite3.connect(STUDENTS_DB)
        cursor = conn.cursor()
        
        # Check if activities table exists
        cursor.execute('''
            SELECT name FROM sqlite_master WHERE type='table' AND name='ACTIVITIES'
        ''')
        
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({'success': True, 'activities': []})
        
        # Get activities for this parent (latest first)
        cursor.execute('''
            SELECT student_name, activity_type, activity_text, timestamp
            FROM ACTIVITIES
            WHERE parent_name = ?
            ORDER BY id DESC
            LIMIT 5
        ''', (session['full_name'],))
        
        activities = []
        for row in cursor.fetchall():
            activities.append({
                'student_name': row[0],
                'activity_type': row[1],
                'activity_text': row[2],
                'timestamp': row[3]
            })
        
        conn.close()
        return jsonify({'success': True, 'activities': activities})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== ENHANCED TEMPLATE FUNCTIONS ====================

@app.context_processor
def inject_user_data():
    """Inject user data into all templates"""
    return {
        'current_user': {
            'id': session.get('user_id'),
            'name': session.get('full_name'),
            'role': session.get('user_role'),
            'email': session.get('email')
        } if 'user_id' in session else None
    }


# ==================== BACKGROUND SERVICES ====================

def start_background_services():
    """Start all background services"""
    location_service.start_tracking()
    print("✅ Background services started")


# ==================== MAIN APPLICATION ====================

if __name__ == "__main__":
    print("🚀 AI Safety Systems - Enhanced Real-time Server")
    print(f"📁 Database: {USERS_DB}")
    print("💡 Default admin: admin/admin123")
    print("💡 Sample driver: mehmet.kaya/driver123")
    print("💡 Sample parent: ayse.yilmaz/parent123")
    print("=" * 60)

    # Start background services
    start_background_services()

    # Run with SocketIO for real-time features
    socketio.run(app, debug=True, host='0.0.0.0', port=5050)


    # Add these routes to your main.py file

    # ==================== ADDITIONAL API ROUTES ====================

    @app.route("/api/current-user")
    @login_required
    def api_current_user():
        """Get current logged-in user information"""
        return jsonify({
            'id': session['user_id'],
            'name': session['full_name'],
            'role': session['user_role'],
            'email': session.get('email'),
            'phone': session.get('phone')
        })


    # ==================== ADD SAMPLE MESSAGES FOR TESTING ====================

    def create_sample_messages():
        """Create sample messages for testing"""
        try:
            conn = sqlite3.connect(USERS_DB)
            cursor = conn.cursor()

            # Check if messages already exist
            cursor.execute('SELECT COUNT(*) FROM messages')
            if cursor.fetchone()[0] > 0:
                conn.close()
                return

            # Create sample messages between parent (id=4) and driver (id=2)
            sample_messages = [
                (2, 4, 'Merhaba! Ben Mehmet, çocuğunuzun şoförüyüm.', 'text'),
                (4, 2, 'Merhaba Mehmet Bey, memnun oldum.', 'text'),
                (2, 4, 'Zeynep bugün otobüse bindi, güvenle okula götürüyorum.', 'text'),
                (4, 2, 'Teşekkür ederim, haberdar ettiğiniz için.', 'text'),
                (2, 4, 'Rica ederim. Her zaman iletişimde kalırız.', 'text'),
            ]

            for sender_id, receiver_id, message_text, message_type in sample_messages:
                cursor.execute('''
                    INSERT INTO messages (sender_id, receiver_id, message_text, message_type, sent_at)
                    VALUES (?, ?, ?, ?, datetime('now', '-' || abs(random() % 60) || ' minutes'))
                ''', (sender_id, receiver_id, message_text, message_type))

            # Create messages between parent (id=5) and driver (id=2)
            sample_messages_2 = [
                (5, 2, 'Merhaba, Ahmet için bugün erken alım mümkün mü?', 'text'),
                (2, 5, 'Tabi, saat kaçta alayım?', 'text'),
                (5, 2, '14:30 gibi olur mu?', 'text'),
                (2, 5, 'Olur, not aldım. 14:30da okulda olacağım.', 'text'),
            ]

            for sender_id, receiver_id, message_text, message_type in sample_messages_2:
                cursor.execute('''
                    INSERT INTO messages (sender_id, receiver_id, message_text, message_type, sent_at)
                    VALUES (?, ?, ?, ?, datetime('now', '-' || abs(random() % 30) || ' minutes'))
                ''', (sender_id, receiver_id, message_text, message_type))

            conn.commit()
            conn.close()
            print("✅ Sample messages created")

        except Exception as e:
            print(f"❌ Error creating sample messages: {e}")


    # ==================== UPDATE THE DATABASE INITIALIZATION ====================

    # Add this to the EnhancedDatabase.__init__ method, after populate_sample_data():
    # create_sample_messages()

    # ==================== IMPROVED SOCKETIO EVENTS ====================

    @socketio.on('join_room')
    def handle_join_room(room_name):
        """Handle joining a specific room"""
        join_room(room_name)
        print(f"User {session.get('full_name', 'Unknown')} joined room: {room_name}")
        emit('room_joined', {'room': room_name})