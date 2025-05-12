import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from flask import Flask, render_template, request, redirect, url_for
from attendance.faceRecognition import load_known_faces, verify_student
from dataManagement.attendanceLogger import log_attendance, get_today_attendance, _init_today_attendance
from config import PROJECT_ROOT
# Flask setup
from config import PROJECT_ROOT

TEMPLATE_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))

UPLOAD_FOLDER = PROJECT_ROOT / "static" / "uploads"

# Load known faces globally ONCE
known_encodings, known_names = load_known_faces()
ALL_STUDENTS = known_names  # Automatically from known_faces

@app.route("/")
def home():
    return render_template("index.html")


_init_today_attendance()
@app.route("/verify", methods=["GET", "POST"])
def verify():
    match_result = None

    if request.method == "POST":
        file = request.files.get("image")
        if file:
            UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
            image_path = UPLOAD_FOLDER / file.filename
            file.save(image_path)

            # Match + Log
            match_result = verify_student(str(image_path), known_encodings, known_names)
            if match_result:
                log_attendance(match_result)

            image_path.unlink()

        return redirect(url_for("verify"))

    present_today = get_today_attendance()
    status_list = [
        (student, "✅ on the service" if student in set(present_today) else "❌ absent")
        for student in sorted(set(ALL_STUDENTS))
    ]

    return render_template("verify.html", match=match_result, status_list=status_list)

if __name__ == "__main__":
    app.run(debug=True)
