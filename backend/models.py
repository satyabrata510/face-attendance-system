from sqlalchemy import Column, Integer, String, DateTime, Float, LargeBinary, ForeignKey, Date, Time, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"


class StudentStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class Student(Base):
    """Student model for storing student information and face encodings."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    roll_no = Column(String(20), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    status = Column(String(20), default=StudentStatus.ACTIVE.value)
    dob = Column(String(50), nullable=True)  # Added Date of Birth column
    hashed_password = Column(String(255), nullable=True)  # Added for student signup/login
    face_encoding = Column(LargeBinary, nullable=True)  # Serialized numpy array
    face_image_path = Column(String(255), nullable=True)
    photo_url = Column(String(500), nullable=True)  # Added for external photo links
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with attendance records
    attendance_records = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")


class Attendance(Base):
    """Attendance model for storing attendance records."""
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    status = Column(String(20), default=AttendanceStatus.PRESENT.value)
    confidence = Column(Float, nullable=True)  # Face recognition confidence
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with student
    student = relationship("Student", back_populates="attendance_records")


class Settings(Base):
    """Settings model for storing application configuration."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
