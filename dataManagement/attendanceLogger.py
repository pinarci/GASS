import csv
from datetime import datetime
from config import ATTENDANCE_FILE

def _init_today_attendance():
    # Clear or create today's CSV file on app start
    with open(ATTENDANCE_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "student"])  # Optional header

def log_attendance(student_name):
    today = datetime.today().strftime('%Y-%m-%d')
    with open(ATTENDANCE_FILE, "r", newline="") as file:
        reader = csv.reader(file)
        if any(row for row in reader if row[1] == student_name and row[0] == today):
            print(f"⚠️ Already logged: {student_name}")
            return

    with open(ATTENDANCE_FILE, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([today, student_name])
        print(f"✅ Successfully logged: {student_name}")

def get_today_attendance():
    today = datetime.today().strftime('%Y-%m-%d')
    with open(ATTENDANCE_FILE, "r") as file:
        reader = csv.reader(file)
        return [row[1] for row in reader if row and row[0] == today and row[1] != "student"]  # skip header
