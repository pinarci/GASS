# Enhanced Face Recognition System - attendance/faceRecognition.py

import face_recognition
import cv2
import os
import numpy as np
from pathlib import Path
import pickle
import logging
from datetime import datetime
import sqlite3

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWN_FACES_DIR = PROJECT_ROOT / "static" / "known_faces"
ENCODINGS_CACHE_FILE = PROJECT_ROOT / "face_encodings_cache.pkl"


class FaceRecognitionSystem:
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.known_ids = []
        self.confidence_threshold = 0.6
        self.tolerance = 0.6

    def load_and_encode_faces(self, force_reload=False):
        """Load faces from directory and create encodings"""

        # Check if cache exists and is recent
        if not force_reload and ENCODINGS_CACHE_FILE.exists():
            try:
                with open(ENCODINGS_CACHE_FILE, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.known_encodings = cache_data['encodings']
                    self.known_names = cache_data['names']
                    self.known_ids = cache_data['ids']
                    logger.info(f"✅ Loaded {len(self.known_names)} faces from cache")
                    return self.known_encodings, self.known_names
            except Exception as e:
                logger.warning(f"Cache loading failed: {e}, rebuilding...")

        # Build encodings from scratch
        logger.info("🔍 Building face encodings...")
        self.known_encodings = []
        self.known_names = []
        self.known_ids = []

        if not KNOWN_FACES_DIR.exists():
            logger.error(f"❌ Known faces directory not found: {KNOWN_FACES_DIR}")
            return [], []

        student_count = 0
        face_count = 0

        # Walk through student directories
        for student_dir in KNOWN_FACES_DIR.iterdir():
            if not student_dir.is_dir():
                continue

            student_name = student_dir.name
            student_count += 1

            logger.info(f"📸 Processing student: {student_name}")

            # Process all images for this student
            student_encodings = []
            valid_images = 0

            for image_file in student_dir.iterdir():
                if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    try:
                        # Load and encode face
                        image = face_recognition.load_image_file(str(image_file))
                        face_encodings = face_recognition.face_encodings(image)

                        if face_encodings:
                            # Use the first (and hopefully only) face found
                            encoding = face_encodings[0]
                            student_encodings.append(encoding)
                            valid_images += 1
                            face_count += 1

                            logger.info(f"  ✅ {image_file.name} - Face encoded")
                        else:
                            logger.warning(f"  ⚠️ {image_file.name} - No face detected")

                    except Exception as e:
                        logger.error(f"  ❌ {image_file.name} - Error: {e}")

            # Calculate average encoding for this student
            if student_encodings:
                if len(student_encodings) > 1:
                    # Average multiple encodings for better accuracy
                    avg_encoding = np.mean(student_encodings, axis=0)
                else:
                    avg_encoding = student_encodings[0]

                self.known_encodings.append(avg_encoding)
                self.known_names.append(student_name)
                self.known_ids.append(student_count)

                logger.info(f"  ✅ Added {student_name} with {valid_images} face(s)")
            else:
                logger.warning(f"  ⚠️ No valid faces found for {student_name}")

        # Cache the encodings
        try:
            cache_data = {
                'encodings': self.known_encodings,
                'names': self.known_names,
                'ids': self.known_ids,
                'created_at': datetime.now().isoformat()
            }
            with open(ENCODINGS_CACHE_FILE, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.info(f"💾 Cached encodings to {ENCODINGS_CACHE_FILE}")
        except Exception as e:
            logger.warning(f"Failed to cache encodings: {e}")

        logger.info(f"🎉 Face recognition system ready:")
        logger.info(f"   📊 Students processed: {student_count}")
        logger.info(f"   📸 Total faces encoded: {face_count}")
        logger.info(f"   ✅ Students with valid faces: {len(self.known_names)}")

        return self.known_encodings, self.known_names

    def verify_student_advanced(self, image_path, min_confidence=0.6):
        """Advanced student verification with confidence scoring"""

        if not self.known_encodings:
            logger.error("❌ No known faces loaded")
            return None, 0.0

        try:
            # Load the image
            unknown_image = face_recognition.load_image_file(image_path)
            unknown_encodings = face_recognition.face_encodings(unknown_image)

            if not unknown_encodings:
                logger.warning("⚠️ No face detected in uploaded image")
                return None, 0.0

            # Use the first face found
            unknown_encoding = unknown_encodings[0]

            # Calculate distances to all known faces
            distances = face_recognition.face_distance(self.known_encodings, unknown_encoding)
            best_match_index = np.argmin(distances)
            best_distance = distances[best_match_index]

            # Convert distance to confidence (lower distance = higher confidence)
            confidence = 1 - best_distance

            if confidence >= min_confidence:
                student_name = self.known_names[best_match_index]
                logger.info(f"✅ Student recognized: {student_name} (confidence: {confidence:.2f})")
                return student_name, confidence
            else:
                logger.warning(f"⚠️ No confident match found (best: {confidence:.2f})")
                return None, confidence

        except Exception as e:
            logger.error(f"❌ Error in face verification: {e}")
            return None, 0.0

    def get_system_stats(self):
        """Get face recognition system statistics"""
        return {
            'total_students': len(self.known_names),
            'total_encodings': len(self.known_encodings),
            'students_list': self.known_names.copy(),
            'cache_exists': ENCODINGS_CACHE_FILE.exists(),
            'confidence_threshold': self.confidence_threshold
        }


# Global face recognition instance
face_system = FaceRecognitionSystem()


# Legacy functions for backward compatibility
def load_known_faces():
    """Load known faces - maintains compatibility with existing code"""
    encodings, names = face_system.load_and_encode_faces()
    return encodings, names


def verify_student(image_path, known_encodings=None, known_names=None, min_confidence=0.6):
    """Verify student - enhanced version with confidence"""
    if known_encodings is None or known_names is None:
        # Use the global system
        student_name, confidence = face_system.verify_student_advanced(image_path, min_confidence)
        return student_name
    else:
        # Legacy mode - use provided encodings
        try:
            unknown_image = face_recognition.load_image_file(image_path)
            unknown_encodings = face_recognition.face_encodings(unknown_image)

            if not unknown_encodings:
                return None

            unknown_encoding = unknown_encodings[0]
            matches = face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=0.6)

            if True in matches:
                match_index = matches.index(True)
                return known_names[match_index]

            return None

        except Exception as e:
            logger.error(f"Error in legacy verification: {e}")
            return None


def rebuild_face_encodings():
    """Force rebuild of face encodings"""
    return face_system.load_and_encode_faces(force_reload=True)


def get_face_recognition_stats():
    """Get face recognition statistics"""
    return face_system.get_system_stats()


# Auto-load faces when module is imported
if __name__ != "__main__":
    try:
        load_known_faces()
    except Exception as e:
        logger.error(f"Failed to auto-load faces: {e}")