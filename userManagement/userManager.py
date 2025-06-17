# Real User Management System - userManagement/userManager.py

import sqlite3
import csv
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "production_users.db"


class UserManager:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_database()

    def init_database(self):
        """Initialize the user database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('parent', 'driver', 'admin')),
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(username)
            )
        ''')

        # Students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                parent_id INTEGER,
                driver_id INTEGER,
                emergency_contact TEXT,
                medical_info TEXT,
                pickup_address TEXT,
                dropoff_address TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES users (id),
                FOREIGN KEY (driver_id) REFERENCES users (id)
            )
        ''')

        # Vehicles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_plate TEXT UNIQUE NOT NULL,
                driver_id INTEGER,
                capacity INTEGER NOT NULL,
                model TEXT,
                year INTEGER,
                gps_device_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_id) REFERENCES users (id)
            )
        ''')

        # Routes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_name TEXT NOT NULL,
                vehicle_id INTEGER,
                start_time TIME NOT NULL,
                end_time TIME,
                route_type TEXT CHECK (route_type IN ('morning', 'afternoon')),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
            )
        ''')

        # Route stops table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS route_stops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id INTEGER,
                student_id INTEGER,
                stop_order INTEGER,
                pickup_time TIME,
                address TEXT,
                latitude REAL,
                longitude REAL,
                FOREIGN KEY (route_id) REFERENCES routes (id),
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')

        # Real-time attendance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT CHECK (event_type IN ('board', 'alight', 'absent')),
                location TEXT,
                confidence_score REAL,
                verified_by INTEGER,
                notes TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (verified_by) REFERENCES users (id)
            )
        ''')

        # Messages table for real communication
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
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("✅ Database initialized with production schema")

    def import_users_from_csv(self, csv_file_path):
        """Import users from CSV file"""
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                users_added = 0

                for row in reader:
                    success = self.add_user(
                        username=row.get('username'),
                        password=row.get('password'),
                        role=row.get('role'),
                        full_name=row.get('full_name'),
                        email=row.get('email'),
                        phone=row.get('phone')
                    )
                    if success:
                        users_added += 1

                logger.info(f"✅ Imported {users_added} users from CSV")
                return users_added

        except Exception as e:
            logger.error(f"❌ Error importing users: {e}")
            return 0

    def add_user(self, username, password, role, full_name, email=None, phone=None):
        """Add a new user to the system"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            password_hash = generate_password_hash(password)

            cursor.execute('''
                INSERT INTO users (username, password_hash, role, full_name, email, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password_hash, role, full_name, email, phone))

            user_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"✅ Added user: {username} ({role}) - {full_name}")
            return user_id

        except sqlite3.IntegrityError as e:
            logger.error(f"❌ User already exists: {username}")
            return None
        except Exception as e:
            logger.error(f"❌ Error adding user: {e}")
            return None

    def add_student(self, student_id, full_name, class_name, parent_username,
                    emergency_contact=None, pickup_address=None, dropoff_address=None):
        """Add a new student and link to parent"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get parent ID
            cursor.execute('SELECT id FROM users WHERE username = ? AND role = "parent"', (parent_username,))
            parent_result = cursor.fetchone()

            if not parent_result:
                logger.error(f"❌ Parent not found: {parent_username}")
                return None

            parent_id = parent_result[0]

            cursor.execute('''
                INSERT INTO students (student_id, full_name, class_name, parent_id, 
                                    emergency_contact, pickup_address, dropoff_address)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (student_id, full_name, class_name, parent_id, emergency_contact, pickup_address, dropoff_address))

            student_db_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"✅ Added student: {full_name} (ID: {student_id}) - Parent: {parent_username}")
            return student_db_id

        except Exception as e:
            logger.error(f"❌ Error adding student: {e}")
            return None

    def assign_driver_to_student(self, student_id, driver_username):
        """Assign a driver to a student"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get driver ID
            cursor.execute('SELECT id FROM users WHERE username = ? AND role = "driver"', (driver_username,))
            driver_result = cursor.fetchone()

            if not driver_result:
                logger.error(f"❌ Driver not found: {driver_username}")
                return False

            driver_id = driver_result[0]

            cursor.execute('UPDATE students SET driver_id = ? WHERE student_id = ?', (driver_id, student_id))

            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"✅ Assigned driver {driver_username} to student {student_id}")
                result = True
            else:
                logger.error(f"❌ Student not found: {student_id}")
                result = False

            conn.close()
            return result

        except Exception as e:
            logger.error(f"❌ Error assigning driver: {e}")
            return False

    def get_students_for_parent(self, parent_username):
        """Get all students for a specific parent"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT s.student_id, s.full_name, s.class_name, s.emergency_contact,
                       d.full_name as driver_name, d.username as driver_username,
                       v.license_plate
                FROM students s
                LEFT JOIN users p ON s.parent_id = p.id
                LEFT JOIN users d ON s.driver_id = d.id
                LEFT JOIN vehicles v ON d.id = v.driver_id
                WHERE p.username = ? AND s.is_active = 1
            ''', (parent_username,))

            students = []
            for row in cursor.fetchall():
                students.append({
                    'student_id': row[0],
                    'full_name': row[1],
                    'class_name': row[2],
                    'emergency_contact': row[3],
                    'driver_name': row[4],
                    'driver_username': row[5],
                    'vehicle_plate': row[6]
                })

            conn.close()
            return students

        except Exception as e:
            logger.error(f"❌ Error getting students for parent: {e}")
            return []

    def get_students_for_driver(self, driver_username):
        """Get all students assigned to a specific driver"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT s.student_id, s.full_name, s.class_name, s.pickup_address,
                       p.full_name as parent_name, p.username as parent_username, p.phone
                FROM students s
                LEFT JOIN users d ON s.driver_id = d.id
                LEFT JOIN users p ON s.parent_id = p.id
                WHERE d.username = ? AND s.is_active = 1
                ORDER BY s.full_name
            ''', (driver_username,))

            students = []
            for row in cursor.fetchall():
                students.append({
                    'student_id': row[0],
                    'full_name': row[1],
                    'class_name': row[2],
                    'pickup_address': row[3],
                    'parent_name': row[4],
                    'parent_username': row[5],
                    'parent_phone': row[6]
                })

            conn.close()
            return students

        except Exception as e:
            logger.error(f"❌ Error getting students for driver: {e}")
            return []

    def log_attendance(self, student_id, event_type, location=None, confidence_score=None):
        """Log real attendance event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO attendance_logs (student_id, event_type, location, confidence_score)
                SELECT s.id, ?, ?, ?
                FROM students s
                WHERE s.student_id = ?
            ''', (event_type, location, confidence_score, student_id))

            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"✅ Logged attendance: {student_id} - {event_type}")
                result = True
            else:
                logger.error(f"❌ Student not found for attendance: {student_id}")
                result = False

            conn.close()
            return result

        except Exception as e:
            logger.error(f"❌ Error logging attendance: {e}")
            return False

    def send_message(self, sender_username, receiver_username, message_text):
        """Send a real message between users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get sender and receiver IDs
            cursor.execute('SELECT id FROM users WHERE username = ?', (sender_username,))
            sender_result = cursor.fetchone()

            cursor.execute('SELECT id FROM users WHERE username = ?', (receiver_username,))
            receiver_result = cursor.fetchone()

            if not sender_result or not receiver_result:
                logger.error(f"❌ User not found for messaging")
                return False

            sender_id = sender_result[0]
            receiver_id = receiver_result[0]

            cursor.execute('''
                INSERT INTO messages (sender_id, receiver_id, message_text)
                VALUES (?, ?, ?)
            ''', (sender_id, receiver_id, message_text))

            message_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"✅ Message sent: {sender_username} → {receiver_username}")
            return message_id

        except Exception as e:
            logger.error(f"❌ Error sending message: {e}")
            return False

    def get_messages_between_users(self, user1_username, user2_username, limit=50):
        """Get message history between two users"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT m.message_text, m.sent_at, m.is_read,
                       sender.username as sender, sender.full_name as sender_name,
                       receiver.username as receiver, receiver.full_name as receiver_name
                FROM messages m
                JOIN users sender ON m.sender_id = sender.id
                JOIN users receiver ON m.receiver_id = receiver.id
                WHERE (sender.username = ? AND receiver.username = ?)
                   OR (sender.username = ? AND receiver.username = ?)
                ORDER BY m.sent_at DESC
                LIMIT ?
            ''', (user1_username, user2_username, user2_username, user1_username, limit))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'text': row[0],
                    'sent_at': row[1],
                    'is_read': row[2],
                    'sender': row[3],
                    'sender_name': row[4],
                    'receiver': row[5],
                    'receiver_name': row[6]
                })

            conn.close()
            return list(reversed(messages))  # Return in chronological order

        except Exception as e:
            logger.error(f"❌ Error getting messages: {e}")
            return []

    def create_sample_data_csv(self):
        """Create sample CSV files for data import"""

        # Sample users CSV
        users_csv = PROJECT_ROOT / "sample_data" / "users.csv"
        users_csv.parent.mkdir(exist_ok=True)

        with open(users_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['username', 'password', 'role', 'full_name', 'email', 'phone'])

            # Sample parents
            writer.writerow(['ayse.yilmaz', 'parent123', 'parent', 'Ayşe Yılmaz', 'ayse@email.com', '0555-111-2222'])
            writer.writerow(
                ['mehmet.demir', 'parent456', 'parent', 'Mehmet Demir', 'mehmet@email.com', '0555-333-4444'])
            writer.writerow(['fatma.kaya', 'parent789', 'parent', 'Fatma Kaya', 'fatma@email.com', '0555-555-6666'])

            # Sample drivers
            writer.writerow(['ali.driver', 'driver123', 'driver', 'Ali Şahin', 'ali@school.edu.tr', '0555-777-8888'])
            writer.writerow(
                ['hasan.driver', 'driver456', 'driver', 'Hasan Özkan', 'hasan@school.edu.tr', '0555-999-0000'])

            # Sample admin
            writer.writerow(['admin', 'admin123', 'admin', 'Okul Yöneticisi', 'admin@school.edu.tr', '0555-100-2000'])

        # Sample students CSV
        students_csv = PROJECT_ROOT / "sample_data" / "students.csv"

        with open(students_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(
                ['student_id', 'full_name', 'class_name', 'parent_username', 'emergency_contact', 'pickup_address'])

            writer.writerow(
                ['STU001', 'Zeynep Yılmaz', '4-A', 'ayse.yilmaz', '0555-111-2223', 'Ataşehir Mah. 1. Sok No:5'])
            writer.writerow(
                ['STU002', 'Ahmet Demir', '3-B', 'mehmet.demir', '0555-333-4445', 'Çamlıca Mah. 2. Cad No:10'])
            writer.writerow(['STU003', 'Elif Kaya', '5-C', 'fatma.kaya', '0555-555-6667', 'Merkez Mah. 3. Sok No:15'])

        logger.info(f"✅ Sample CSV files created in {users_csv.parent}")
        return users_csv, students_csv


# Global user manager instance
user_manager = UserManager()