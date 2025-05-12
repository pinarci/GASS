import os
import face_recognition
from pathlib import Path
from config import KNOWN_FACES_DIR

def load_known_faces():
    known_encodings = []
    known_names = []
    seen_names = set()

    for name in os.listdir(KNOWN_FACES_DIR):
        person_dir = os.path.join(KNOWN_FACES_DIR, name)
        if not os.path.isdir(person_dir):
            continue

        for filename in os.listdir(person_dir):
            img_path = os.path.join(person_dir, filename)
            image = face_recognition.load_image_file(img_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_encodings.append(encodings[0])
                known_names.append(name)

        seen_names.add(name)  # Add only unique names

    return known_encodings, list(seen_names)


def verify_student(upload_path, known_encodings, known_names):
    print(f"🔍 Verifying image: {upload_path}")
    try:
        image = face_recognition.load_image_file(upload_path)
        upload_encodings = face_recognition.face_encodings(image)

        if not upload_encodings:
            print("❌ No face found in uploaded image.")
            return None

        upload_encoding = upload_encodings[0]
        distances = face_recognition.face_distance(known_encodings, upload_encoding)
        results = face_recognition.compare_faces(known_encodings, upload_encoding)

        print(f"📏 Face distances: {distances}")
        print(f"🔗 Match results: {results}")

        if True in results:
            matched_index = results.index(True)
            matched_name = known_names[matched_index]
            print(f"🎯 MATCH: {matched_name}")
            return matched_name
        else:
            print("❌ No match found.")
            return None

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return None
