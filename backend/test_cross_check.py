import sqlite3
import pickle
import numpy as np
import face_recognition

def test_db():
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, face_encoding, photo_url FROM students WHERE face_encoding IS NOT NULL;")
    rows = cursor.fetchall()
    
    known_faces = []
    student_names = []
    
    print("Checking database face encodings...")
    for uid, name, encoding_bytes, url in rows:
        encoding = pickle.loads(encoding_bytes)
        known_faces.append(encoding)
        student_names.append(name)
        print(f"Loaded {name} (ID {uid})")
        
    print("\nCross-matching all known faces:")
    for i, unknown_encoding in enumerate(known_faces):
        distances = face_recognition.face_distance(known_faces, unknown_encoding)
        print(f"\n{student_names[i]} distances:")
        for j, dist in enumerate(distances):
            print(f"  vs {student_names[j]}: {dist:.4f}")

if __name__ == '__main__':
    test_db()
