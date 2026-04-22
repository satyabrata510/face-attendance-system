from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, time, timedelta
from typing import List, Dict

from database import get_db
from models import Student, Attendance, AttendanceStatus, Settings
from schemas import (
    AttendanceRecord,
    AttendanceMarkResponse,
    DetectedFace,
    TodayAttendanceResponse
)
from services.face_recognition_service import face_service
from routers.auth import get_current_active_user

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])

import logging
import os

# Set up logging for error tracking
logger = logging.getLogger("attendance_router")
logger.setLevel(logging.DEBUG)
log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug_attendance.log")
handler = logging.FileHandler(log_file)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# In-memory cooldown cache: {student_id: last_detection_timestamp}
# Prevents repeated face recognition processing for the same student
_detection_cooldown: Dict[int, datetime] = {}
COOLDOWN_SECONDS = 60  # Skip re-processing for 60 seconds after a successful detection


def get_setting(db: Session, key: str, default: str) -> str:
    """Get a setting value from the database."""
    setting = db.query(Settings).filter(Settings.key == key).first()
    return setting.value if setting else default


@router.post("/mark", response_model=AttendanceMarkResponse)
async def mark_attendance(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_active_user)
):
    """
    Mark attendance by recognizing faces in the uploaded image.
    Returns list of detected and recognized students.
    """
    # Read image bytes
    image_bytes = await file.read()
    
    # Check if any faces are detected
    face_count = face_service.detect_faces(image_bytes)
    if face_count == 0:
        return AttendanceMarkResponse(
            success=False,
            message="No faces detected in the image",
            detected_faces=[]
        )
    
    # Get all students with registered faces
    query = db.query(Student).filter(
        Student.face_encoding.isnot(None),
        Student.status == "Active"
    )
    
    # Filter by branch if teacher
    if hasattr(current_user, "role") and current_user.role == "teacher" and hasattr(current_user, "branch"):
        query = query.filter(Student.department == current_user.branch)
        
    students_with_faces = query.all()
    
    if not students_with_faces:
        return AttendanceMarkResponse(
            success=False,
            message="No students with registered faces found",
            detected_faces=[]
        )
    
    # Get recognition sensitivity from settings
    sensitivity = int(get_setting(db, "face_recognition_sensitivity", "75"))
    
    # Prepare known encodings
    known_encodings = [
        (student.id, student.face_encoding) 
        for student in students_with_faces
    ]
    
    # Compare faces
    matches = face_service.compare_faces(known_encodings, image_bytes, sensitivity)
    
    if not matches:
        return AttendanceMarkResponse(
            success=False,
            message=f"Detected {face_count} face(s) but no matches found",
            detected_faces=[]
        )
    
    # Determine status (always present if recognized)
    status = AttendanceStatus.PRESENT.value
    now = datetime.now()
    current_time = now.time()
    current_date = now.date()
    
    detected_faces = []
    
    for student_id, confidence in matches:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            continue
        
        # Check if already marked today
        existing = db.query(Attendance).filter(
            Attendance.student_id == student_id,
            Attendance.date == current_date
        ).first()
        
        if existing:
            detected_faces.append(DetectedFace(
                id=student.id,
                name=f"{student.name} (already marked)",
                confidence=confidence
            ))
            continue
        
        # Create attendance record
        attendance = Attendance(
            student_id=student_id,
            date=current_date,
            time=current_time,
            status=status,
            confidence=confidence
        )
        db.add(attendance)
        
        detected_faces.append(DetectedFace(
            id=student.id,
            name=student.name,
            confidence=confidence
        ))
    
    db.commit()
    
    return AttendanceMarkResponse(
        success=True,
        message=f"Marked attendance for {len(detected_faces)} student(s)",
        detected_faces=detected_faces
    )


@router.post("/mark-by-face")
async def mark_attendance_by_face(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_active_user)
):
    """
    Mark attendance for all recognized faces in the image (multi-face/webcam mode).
    Returns list of matched students.
    Only stops scanning if at least one new attendance is marked.
    If multiple faces are detected but none match, it returns success=False but provides face_count.
    """
    try:
        logger.info(f"Mark attendance request started for user: {getattr(current_user, 'username', 'unknown')}")
        
        # Clean up expired cooldown entries
        now = datetime.now()
        expired_ids = [
            sid for sid, ts in list(_detection_cooldown.items())
            if (now - ts).total_seconds() > COOLDOWN_SECONDS
        ]
        for sid in expired_ids:
            if sid in _detection_cooldown:
                del _detection_cooldown[sid]

        # Read image bytes
        image_bytes = await file.read()
        
        # Check if any faces are detected
        face_count = face_service.detect_faces(image_bytes)
        logger.debug(f"Detected {face_count} faces in image.")
        
        if face_count == 0:
            return {
                "success": False,
                "message": "No faces detected in the camera view",
                "face_count": 0,
                "stop_scanning": False
            }
        
        # Get all students with registered faces and active status
        query = db.query(Student).filter(
            Student.face_encoding.isnot(None),
            Student.status == "Active"
        )
        
        # Filter by branch if teacher
        if hasattr(current_user, "role") and current_user.role == "teacher" and hasattr(current_user, "branch") and current_user.branch:
            teacher_branch = current_user.branch.strip().upper()
            query = query.filter(func.upper(Student.department) == teacher_branch)
            
        students_with_faces = query.all()
        
        if not students_with_faces:
            branch_info = current_user.branch if hasattr(current_user, "branch") else "system"
            return {
                "success": False,
                "message": f"No active registered students found in {branch_info}",
                "face_count": face_count,
                "stop_scanning": False
            }
        
        # Get recognition sensitivity
        raw_val = get_setting(db, "face_recognition_sensitivity", "75")
        try:
            sensitivity = int(float(raw_val))
        except (ValueError, TypeError):
            sensitivity = 75
        
        # Prepare known encodings
        known_encodings = [(s.id, s.face_encoding) for s in students_with_faces]
        
        # Compare all detected faces with known faces
        matches = face_service.compare_faces(known_encodings, image_bytes, sensitivity)
        
        if not matches:
            logger.debug(f"{face_count} face(s) detected but none matched registered students.")
            return {
                "success": False,
                "message": f"Seen {face_count} face(s), but none are registered in this branch.",
                "face_count": face_count,
                "stop_scanning": False
            }
        
        # We have matches! Process all of them.
        processed_students = []
        any_newly_marked = False
        current_date = now.date()
        current_time = now.time()
        
        for student_id, confidence in matches:
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                continue
                
            # Check cooldown
            last_check = _detection_cooldown.get(student_id)
            is_in_cooldown = last_check and (now - last_check).total_seconds() < COOLDOWN_SECONDS
            
            # Check database
            existing = db.query(Attendance).filter(
                Attendance.student_id == student_id,
                Attendance.date == current_date
            ).first()
            
            already_marked = existing is not None
            
            # Record detection if not already marked or in cooldown
            if not already_marked and not is_in_cooldown:
                # Mark as present
                new_attendance = Attendance(
                    student_id=student.id,
                    date=current_date,
                    time=current_time,
                    status="present",
                    confidence=confidence
                )
                db.add(new_attendance)
                _detection_cooldown[student_id] = now
                any_newly_marked = True
                
                processed_students.append({
                    "student_id": student.id,
                    "student_name": student.name,
                    "confidence": confidence,
                    "already_marked": False
                })
            elif already_marked:
                processed_students.append({
                    "student_id": student.id,
                    "student_name": student.name,
                    "confidence": confidence,
                    "already_marked": True
                })
        
        if any_newly_marked:
            db.commit()
            logger.info(f"Marked attendance for {len([s for s in processed_students if not s['already_marked']])} new students.")
        
        return {
            "success": True,
            "message": f"Detected {len(processed_students)} registered student(s)",
            "face_count": face_count,
            "students": processed_students,
            "stop_scanning": any_newly_marked # Stop only if we actually marked someone new
        }
        
    except Exception as e:
        if db:
            db.rollback()
        logger.exception("CRITICAL ERROR in mark_attendance_by_face")
        return {
            "success": False,
            "message": f"Server error: {str(e)}",
            "face_count": 0,
            "stop_scanning": False
        }


@router.post("/clear-cooldown")
def clear_detection_cooldown():
    """Clear the detection cooldown cache. Call this when resuming scanning."""
    _detection_cooldown.clear()
    return {"success": True, "message": "Detection cooldown cleared"}


@router.post("/mark/{student_id}")
def mark_attendance_manual(
    student_id: int,
    status: str = "present",
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_active_user)
):
    """Manually mark attendance for a student (without face recognition)."""
    # Filter by branch if teacher
    query = db.query(Student).filter(Student.id == student_id)
    if hasattr(current_user, "role") and current_user.role == "teacher" and hasattr(current_user, "branch") and current_user.branch:
        teacher_branch = current_user.branch.strip().upper()
        query = query.filter(func.upper(Student.department) == teacher_branch)
    
    student = query.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found in your branch")
    
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    
    # Check if already marked
    existing = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.date == current_date
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Attendance already marked for today")
    
    attendance = Attendance(
        student_id=student_id,
        date=current_date,
        time=current_time,
        status=status,
        confidence=100.0
    )
    db.add(attendance)
    db.commit()
    
    return {"message": f"{student.name} marked as {status}"}


@router.get("/today", response_model=TodayAttendanceResponse)
def get_today_attendance(
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_active_user)
):
    """Get today's attendance summary and records."""
    today = date.today()
    
    # Base queries
    query = db.query(Student).filter(Student.status == "Active")
    att_query = db.query(Attendance).filter(Attendance.date == today)
    
    # Role-based filtering
    if hasattr(current_user, "role"):
        if current_user.role == "teacher" and hasattr(current_user, "branch") and current_user.branch:
            teacher_branch = current_user.branch.strip().upper()
            query = query.filter(func.upper(Student.department) == teacher_branch)
            att_query = att_query.join(Student).filter(func.upper(Student.department) == teacher_branch)
        elif current_user.role == "student":
            query = query.filter(Student.id == current_user.id)
            att_query = att_query.filter(Attendance.student_id == current_user.id)
            
    total_students = query.count()
    records = att_query.all()
    
    present_count = sum(1 for r in records if r.status in ["present", "Present"])
    late_count = sum(1 for r in records if r.status in ["late", "Late"])
    half_day_count = sum(1 for r in records if r.status in ["Half Day"])
    absent_count = total_students - present_count - late_count - half_day_count
    
    attendance_rate = round((present_count + late_count + (half_day_count * 0.5)) / total_students * 100, 1) if total_students > 0 else 0
    
    # Build response records
    attendance_records = []
    for record in records:
        student = db.query(Student).filter(Student.id == record.student_id).first()
        if student:
            attendance_records.append(AttendanceRecord(
                id=record.id,
                student_id=record.student_id,
                student_name=student.name,
                date=record.date,
                time=record.time,
                status=record.status,
                confidence=record.confidence
            ))
    
    return TodayAttendanceResponse(
        total_students=total_students,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        half_day_count=half_day_count,
        attendance_rate=attendance_rate,
        records=attendance_records
    )


@router.get("/recent")
def get_recent_attendance(
    limit: int = 10, 
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_active_user)
):
    """Get recent attendance activity."""
    query = db.query(Attendance)
    
    # Role-based filtering
    if hasattr(current_user, "role"):
        if current_user.role == "teacher" and hasattr(current_user, "branch") and current_user.branch:
            teacher_branch = current_user.branch.strip().upper()
            query = query.join(Student).filter(func.upper(Student.department) == teacher_branch)
        elif current_user.role == "student":
            query = query.filter(Attendance.student_id == current_user.id)
    
    records = query.order_by(
        Attendance.date.desc(), 
        Attendance.time.desc()
    ).limit(limit).all()
    
    result = []
    for record in records:
        student = db.query(Student).filter(Student.id == record.student_id).first()
        if student:
            result.append({
                "id": record.id,
                "name": student.name,
                "time": record.time.strftime("%I:%M %p") if record.time else "N/A",
                "status": record.status,
                "date": record.date.isoformat()
            })
    
    return result


@router.get("/{attendance_date}")
def get_attendance_by_date(
    attendance_date: str, 
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_active_user)
):
    """Get attendance records for a specific date."""
    try:
        target_date = datetime.strptime(attendance_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get attendance records for a specific date
    att_query = db.query(Attendance).filter(Attendance.date == target_date)
    
    # Filter by branch if teacher
    if hasattr(current_user, "role") and current_user.role == "teacher" and hasattr(current_user, "branch") and current_user.branch:
        teacher_branch = current_user.branch.strip().upper()
        att_query = att_query.join(Student).filter(func.upper(Student.department) == teacher_branch)
    
    records = att_query.all()
    
    return [
        {
            "id": r.id,
            "student_id": r.student_id,
            "student_name": db.query(Student.name).filter(Student.id == r.student_id).scalar(),
            "date": r.date.isoformat(),
            "time": r.time.strftime("%I:%M %p") if r.time else "N/A",
            "status": r.status,
            "confidence": r.confidence
        }
        for r in records
    ]
