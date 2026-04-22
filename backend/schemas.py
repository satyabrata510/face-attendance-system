from pydantic import BaseModel
from datetime import datetime, date, time
from typing import Optional, List


# ==================== Auth Schemas ====================

class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = "admin"
    student_id: Optional[int] = None
    branch: Optional[str] = None


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Student Schemas ====================

class StudentBase(BaseModel):
    name: str
    roll_no: str
    department: str
    dob: Optional[str] = None
    photo_url: Optional[str] = None


class StudentCreate(StudentBase):
    pass

class StudentSignup(StudentBase):
    password: str


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    roll_no: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    photo_url: Optional[str] = None


class StudentResponse(StudentBase):
    id: int
    status: str
    photo_url: Optional[str] = None
    face_image_url: Optional[str] = None
    has_face_registered: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    students: List[StudentResponse]
    total: int


class StudentImportResponse(BaseModel):
    success: bool
    imported_count: int
    failed_count: int
    message: str


# ==================== Attendance Schemas ====================

class AttendanceMarkRequest(BaseModel):
    """Request to mark attendance - image will be sent as file upload."""
    pass


class AttendanceRecord(BaseModel):
    id: int
    student_id: int
    student_name: str
    date: date
    time: time
    status: str
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


class DetectedFace(BaseModel):
    id: int
    name: str
    confidence: float


class AttendanceMarkResponse(BaseModel):
    success: bool
    message: str
    detected_faces: List[DetectedFace] = []


class TodayAttendanceResponse(BaseModel):
    total_students: int
    present_count: int
    absent_count: int
    late_count: int
    half_day_count: int = 0
    attendance_rate: float
    records: List[AttendanceRecord]


# ==================== Dashboard/Reports Schemas ====================

class DashboardStats(BaseModel):
    total_students: int
    present_today: int
    absent_today: int
    attendance_rate: float


class WeeklyTrend(BaseModel):
    date: str
    present: int
    absent: int


class MonthlyTrend(BaseModel):
    month: str
    attendance: float


class DepartmentStats(BaseModel):
    name: str
    value: int


class RecentActivity(BaseModel):
    id: int
    name: str
    time: str
    status: str


class DashboardResponse(BaseModel):
    stats: DashboardStats
    weekly_trend: List[WeeklyTrend]
    recent_activity: List[RecentActivity]


# ==================== Settings Schemas ====================

class SettingsUpdate(BaseModel):
    face_recognition_sensitivity: Optional[int] = None
    notifications_enabled: Optional[bool] = None
    low_attendance_alert: Optional[bool] = None
    auto_refresh_interval: Optional[int] = None
    email_notifications: Optional[bool] = None


class SettingsResponse(BaseModel):
    face_recognition_sensitivity: int = 75
    notifications_enabled: bool = True
    low_attendance_alert: bool = True
    auto_refresh_interval: int = 5
    email_notifications: bool = False


# ==================== Face Registration Schemas ====================

class FaceRegistrationResponse(BaseModel):
    success: bool
    message: str
    student_id: Optional[int] = None
