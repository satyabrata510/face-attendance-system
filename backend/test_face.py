import sqlite3
import pickle
import numpy as np

# Connect to database
conn = sqlite3.connect('attendance.db')
cursor = conn.cursor()

# Get student 2 encoding
cursor.execute("SELECT name, face_encoding FROM students WHERE id = 2;")
row = cursor.fetchone()
if not row:
    print("Student not found")
    exit(1)
    
name, encoding_bytes = row
print(f"Student: {name}")

try:
    encoding = pickle.loads(encoding_bytes)
    print(f"Encoding shape: {encoding.shape}")
    print(f"Encoding array sample: {encoding[:5]}")
except Exception as e:
    print(f"Error unpickling: {e}")
