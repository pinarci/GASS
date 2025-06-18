import sqlite3
import face_recognition
import pickle
import os

def create_database():
    """Create the database and STUDENT table"""
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # Create STUDENT table with 5 face encoding columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS STUDENT (
            full_name TEXT PRIMARY KEY,
            father_name TEXT NOT NULL,
            mother_name TEXT NOT NULL,
            class TEXT NOT NULL,
            gender TEXT NOT NULL,
            face_encoding_1 BLOB,
            face_encoding_2 BLOB,
            face_encoding_3 BLOB,
            face_encoding_4 BLOB,
            face_encoding_5 BLOB,
            attendance BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database 'students.db' created successfully with STUDENT table.")

def get_face_encoding_from_photo(photo_path):
    """Get face encoding from a single photo"""
    if not os.path.exists(photo_path):
        print(f"Error: Photo file '{photo_path}' not found.")
        return None
    
    try:
        # Load image and get face encoding
        image = face_recognition.load_image_file(photo_path)
        face_encodings = face_recognition.face_encodings(image)
        
        if len(face_encodings) == 0:
            print(f"Error: No face found in the image '{photo_path}'.")
            return None
        
        # Get the first face encoding and convert to binary data
        face_encoding = face_encodings[0]
        return pickle.dumps(face_encoding)
        
    except Exception as e:
        print(f"Error processing image '{photo_path}': {e}")
        return None

def add_student():
    """Add a new student to the database"""
    # Get student information from user
    full_name = input("Enter full name: ")
    father_name = input("Enter father name: ")
    mother_name = input("Enter mother name: ")
    class_name = input("Enter class: ")
    
    # Get gender with validation
    while True:
        gender = input("Enter gender (M/F or Male/Female): ").strip().upper()
        if gender in ['M', 'MALE', 'F', 'FEMALE']:
            # Normalize to M or F
            gender = 'M' if gender in ['M', 'MALE'] else 'F'
            break
        else:
            print("Please enter M/F or Male/Female")
    
    print("\nPlease provide 5 photos for the student:")
    face_encoding_blobs = []
    
    # Get 5 photo paths and process them
    for i in range(1, 6):
        while True:
            photo_path = input(f"Enter photo {i} path (or 'skip' to leave empty): ")
            
            if photo_path.lower() == 'skip':
                face_encoding_blobs.append(None)
                break
            
            face_encoding_blob = get_face_encoding_from_photo(photo_path)
            if face_encoding_blob is not None:
                face_encoding_blobs.append(face_encoding_blob)
                print(f"✓ Photo {i} processed successfully.")
                break
            else:
                print(f"Please try again for photo {i}.")
    
    # Check if at least one photo was processed
    if all(blob is None for blob in face_encoding_blobs):
        print("Error: At least one valid photo is required.")
        return
    
    try:
        # Insert into database
        conn = sqlite3.connect('students.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO STUDENT (full_name, father_name, mother_name, class, gender,
                               face_encoding_1, face_encoding_2, face_encoding_3, 
                               face_encoding_4, face_encoding_5, attendance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (full_name, father_name, mother_name, class_name, gender,
              face_encoding_blobs[0], face_encoding_blobs[1], face_encoding_blobs[2], 
              face_encoding_blobs[3], face_encoding_blobs[4], False))
        
        conn.commit()
        conn.close()
        
        valid_photos = sum(1 for blob in face_encoding_blobs if blob is not None)
        print(f"Student '{full_name}' added successfully with {valid_photos} photo(s).")
        
    except sqlite3.IntegrityError:
        print(f"Error: A student with the name '{full_name}' already exists in the database.")
    except Exception as e:
        print(f"Error adding student: {e}")

def view_students():
    """View all students in the database (without face encodings)"""
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    cursor.execute('''SELECT full_name, father_name, mother_name, class, gender, attendance,
                     CASE WHEN face_encoding_1 IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN face_encoding_2 IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN face_encoding_3 IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN face_encoding_4 IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN face_encoding_5 IS NOT NULL THEN 1 ELSE 0 END as photo_count
                     FROM STUDENT''')
    students = cursor.fetchall()
    
    if students:
        print("\nStudents in database:")
        print("-" * 115)
        print(f"{'Full Name':<20} {'Father Name':<20} {'Mother Name':<20} {'Class':<10} {'Gender':<8} {'Photos':<8} {'Attendance':<10}")
        print("-" * 115)
        for student in students:
            attendance_status = "Present" if student[5] else "Absent"
            print(f"{student[0]:<20} {student[1]:<20} {student[2]:<20} {student[3]:<10} {student[4]:<8} {student[6]:<8} {attendance_status:<10}")
    else:
        print("No students found in the database.")
    
    conn.close()

def update_gender():
    """Update gender for existing students"""
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # First, check if gender column exists
    cursor.execute("PRAGMA table_info(STUDENT)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'gender' not in columns:
        print("Adding gender column to existing database...")
        cursor.execute('ALTER TABLE STUDENT ADD COLUMN gender TEXT')
        conn.commit()
        print("Gender column added successfully.")
    
    # Show students with missing gender
    cursor.execute('SELECT full_name FROM STUDENT WHERE gender IS NULL OR gender = ""')
    students_without_gender = cursor.fetchall()
    
    if not students_without_gender:
        print("All students already have gender information.")
        conn.close()
        return
    
    print(f"\nFound {len(students_without_gender)} students without gender information:")
    for student in students_without_gender:
        print(f"- {student[0]}")
    
    print("\nUpdating gender information...")
    
    for student in students_without_gender:
        student_name = student[0]
        print(f"\nUpdating: {student_name}")
        
        while True:
            gender = input("Enter gender (M/F or Male/Female): ").strip().upper()
            if gender in ['M', 'MALE', 'F', 'FEMALE']:
                # Normalize to M or F
                gender = 'M' if gender in ['M', 'MALE'] else 'F'
                break
            else:
                print("Please enter M/F or Male/Female")
        
        # Update the student's gender
        cursor.execute('UPDATE STUDENT SET gender = ? WHERE full_name = ?', (gender, student_name))
        print(f"✓ Updated {student_name} - Gender: {gender}")
    
    conn.commit()
    conn.close()
    print(f"\nSuccessfully updated gender information for {len(students_without_gender)} student(s).")

def main():
    """Main function to run the application"""
    create_database()
    
    while True:
        print("\n=== Student Database Management ===")
        print("1. Add new student")
        print("2. View all students")
        print("3. Update gender for existing students")
        print("4. Exit")
        
        choice = input("Enter your choice (1-4): ")
        
        if choice == '1':
            add_student()
        elif choice == '2':
            view_students()
        elif choice == '3':
            update_gender()
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
