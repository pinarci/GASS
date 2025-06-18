import cv2
import face_recognition
import sqlite3
import pickle

def load_known_faces_from_db():
    """Load face encodings and names from the database"""
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    cursor.execute('''SELECT full_name, face_encoding_1, face_encoding_2, 
                     face_encoding_3, face_encoding_4, face_encoding_5 FROM STUDENT''')
    students = cursor.fetchall()
    
    known_face_encodings = []
    known_face_names = []
    
    for student in students:
        full_name = student[0]
        
        # Process all 5 face encodings for this student
        for i in range(1, 6):
            face_encoding_blob = student[i]
            
            if face_encoding_blob is not None:  # Only process non-null encodings
                # Deserialize the face encoding from binary data
                face_encoding = pickle.loads(face_encoding_blob)
                
                known_face_encodings.append(face_encoding)
                known_face_names.append(full_name)
    
    conn.close()
    return known_face_encodings, known_face_names

def mark_attendance(student_name):
    """Toggle attendance for the recognized student"""
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # First, get the current attendance value
    cursor.execute('SELECT attendance FROM STUDENT WHERE full_name = ?', (student_name,))
    result = cursor.fetchone()
    
    if result:
        current_attendance = result[0]
        # Toggle the attendance value (0 becomes 1, 1 becomes 0)
        new_attendance = 1 if current_attendance == 0 else 0
        
        # Update attendance with the toggled value
        cursor.execute('UPDATE STUDENT SET attendance = ? WHERE full_name = ?', (new_attendance, student_name))
        
        # Check if the update was successful
        if cursor.rowcount > 0:
            status = "boarded the bus" if new_attendance == 1 else "got off the bus"
            print(f"Attendance toggled for {student_name}: {current_attendance} -> {new_attendance} ({status})")
    else:
        print(f"Student {student_name} not found in database")
    
    conn.commit()
    conn.close()

webcam_image=cv2.VideoCapture(0)

# Load known faces from database
known_face_encodings, known_face_names = load_known_faces_from_db()

if len(known_face_encodings) == 0:
    print("No students found in database. Please add students first using creatingdb.py")
    webcam_image.release()
    cv2.destroyAllWindows()
    exit()

print(f"Loaded {len(known_face_encodings)} face encodings from database")
unique_students = list(set(known_face_names))
print(f"Students in database: {unique_students}")

# Keep track of students whose attendance has already been marked
attendance_marked = set()

all_face_locations=[]
all_face_encodings=[]

while True:
    ret, current_frame=webcam_image.read()
    all_face_locations=face_recognition.face_locations(current_frame,number_of_times_to_upsample=1 ,model="cnn")
    all_face_encodings=face_recognition.face_encodings(current_frame,all_face_locations)
    for current_face_location, current_face_encoding in zip(all_face_locations, all_face_encodings):
        top_pos, right_pos, bottom_pos, left_pos = current_face_location
 
        
        all_matches=face_recognition.compare_faces(known_face_encodings, current_face_encoding)
        
        name="unknown"
        if True in all_matches:
            first_match_index=all_matches.index(True)
            name=known_face_names[first_match_index]
            
            # Mark attendance if not already marked for this student
            if name not in attendance_marked:
                mark_attendance(name)
                attendance_marked.add(name)
        
        cv2.rectangle(current_frame, (left_pos, top_pos),(right_pos, bottom_pos), (255,0,0), 2)
        font=cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(current_frame, name, (left_pos,top_pos-20), font, 0.5, (255,255,255),1)
        
    cv2.imshow("Video", current_frame)
    if cv2.waitKey(1) & 0xFF ==ord ('q'):
        break
webcam_image.release()
cv2.destroyAllWindows()