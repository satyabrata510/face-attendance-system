from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from typing import List
import csv
import io

from database import get_db
from models import Student, Attendance
from schemas import (
    DashboardStats,
    DashboardResponse,
    WeeklyTrend,
    MonthlyTrend,
    DepartmentStats,
    RecentActivity
)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Get dashboard statistics and data."""
    today = date.today()
    
    # Get total active students
    total_students = db.query(Student).filter(Student.status == "Active").count()
    
    # Get today's attendance
    today_records = db.query(Attendance).filter(Attendance.date == today).all()
    present_today = sum(1 for r in today_records if r.status in ["present", "Present"])
    late_today = sum(1 for r in today_records if r.status in ["late", "Late"])
    absent_today = total_students - present_today - late_today
    
    attendance_rate = round((present_today + late_today) / total_students * 100, 1) if total_students > 0 else 0
    
    # Get weekly trend (last 7 days)
    weekly_trend = []
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        day_records = db.query(Attendance).filter(Attendance.date == target_date).all()
        present = sum(1 for r in day_records if r.status in ["present", "Present", "late", "Late"])
        absent = total_students - present
        weekly_trend.append(WeeklyTrend(
            date=target_date.strftime("%a"),
            present=present,
            absent=absent
        ))
    
    # Get recent activity
    recent_records = db.query(Attendance).order_by(
        Attendance.created_at.desc()
    ).limit(8).all()
    
    recent_activity = []
    for record in recent_records:
        student = db.query(Student).filter(Student.id == record.student_id).first()
        if student:
            time_str = record.time.strftime("%I:%M %p") if record.time else "Absent"
            if record.status in ["absent", "Absent"]:
                time_str = "Absent"
            recent_activity.append(RecentActivity(
                id=record.id,
                name=student.name,
                time=time_str,
                status=record.status
            ))
    
    return DashboardResponse(
        stats=DashboardStats(
            total_students=total_students,
            present_today=present_today + late_today,
            absent_today=absent_today,
            attendance_rate=attendance_rate
        ),
        weekly_trend=weekly_trend,
        recent_activity=recent_activity
    )


@router.get("/weekly")
def get_weekly_trend(db: Session = Depends(get_db)):
    """Get weekly attendance trend data."""
    today = date.today()
    total_students = db.query(Student).filter(Student.status == "Active").count()
    
    weekly_data = []
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        day_records = db.query(Attendance).filter(Attendance.date == target_date).all()
        present = sum(1 for r in day_records if r.status in ["present", "Present", "late", "Late"])
        absent = total_students - present
        weekly_data.append({
            "date": target_date.strftime("%a"),
            "present": present,
            "absent": absent
        })
    
    return weekly_data


@router.get("/monthly")
def get_monthly_trend(db: Session = Depends(get_db)):
    """Get monthly attendance trend data."""
    today = date.today()
    total_students = db.query(Student).filter(Student.status == "Active").count()
    
    monthly_data = []
    for i in range(5, -1, -1):
        # Calculate the first day of each month
        target_month = today.month - i
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        first_day = date(target_year, target_month, 1)
        if target_month == 12:
            last_day = date(target_year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(target_year, target_month + 1, 1) - timedelta(days=1)
        
        # Get attendance records for this month
        month_records = db.query(Attendance).filter(
            Attendance.date >= first_day,
            Attendance.date <= last_day
        ).all()
        
        # Calculate average attendance
        if month_records and total_students > 0:
            days_with_records = len(set(r.date for r in month_records))
            present_count = sum(1 for r in month_records if r.status in ["present", "Present", "late", "Late"])
            if days_with_records > 0:
                avg_daily = present_count / days_with_records
                attendance_pct = round(avg_daily / total_students * 100, 1)
            else:
                attendance_pct = 0
        else:
            attendance_pct = 0
        
        monthly_data.append({
            "month": first_day.strftime("%b"),
            "attendance": attendance_pct
        })
    
    return monthly_data


@router.get("/department")
def get_department_stats(db: Session = Depends(get_db)):
    """Get department-wise student distribution."""
    departments = db.query(
        Student.department,
        func.count(Student.id).label('count')
    ).filter(
        Student.status == "Active"
    ).group_by(Student.department).all()
    
    return [{"name": dept, "value": count} for dept, count in departments]


@router.get("/export/csv")
def export_csv(
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    """Export attendance records as CSV."""
    query = db.query(Attendance)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    records = query.order_by(Attendance.date.desc(), Attendance.time.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Student Name", "Roll No", "Department", "Time", "Status", "Confidence"])
    
    for record in records:
        student = db.query(Student).filter(Student.id == record.student_id).first()
        if student:
            writer.writerow([
                record.date.isoformat(),
                student.name,
                student.roll_no,
                student.department,
                record.time.strftime("%H:%M") if record.time else "N/A",
                record.status,
                f"{record.confidence}%" if record.confidence else "N/A"
            ])
    
    output.seek(0)
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_report.csv"}
    )


@router.get("/records")
def get_attendance_records(
    start_date: str = None,
    end_date: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get detailed attendance records with filters."""
    query = db.query(Attendance)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Attendance.date <= end)
        except ValueError:
            pass
    
    records = query.order_by(
        Attendance.date.desc(), 
        Attendance.time.desc()
    ).limit(limit).all()
    
    result = []
    for record in records:
        student = db.query(Student).filter(Student.id == record.student_id).first()
        if student:
            result.append({
                "date": record.date.isoformat(),
                "student": student.name,
                "time": record.time.strftime("%H:%M") if record.time else "N/A",
                "status": record.status.capitalize()
            })
    
    return result


@router.get("/student/{student_id}")
def get_student_report(
    student_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed attendance report for an individual student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    records = db.query(Attendance).filter(Attendance.student_id == student_id).order_by(Attendance.date.desc()).all()
    
    total_days = len(records)
    present_count = sum(1 for r in records if r.status.lower() == "present")
    late_count = sum(1 for r in records if r.status.lower() == "late")
    absent_count = sum(1 for r in records if r.status.lower() == "absent")
    
    # Calculate attendance starting from creation date until today
    start_date = student.created_at.date() if student.created_at else date.today()
    today = date.today()
    
    # Simple calculation based on records
    attendance_rate = 0
    if total_days > 0:
        attendance_rate = round(((present_count + late_count) / total_days) * 100, 1)

    formatted_records = []
    for r in records:
        formatted_records.append({
            "date": r.date.isoformat(),
            "time": r.time.strftime("%H:%M") if r.time else "N/A",
            "status": r.status.capitalize(),
            "confidence": f"{r.confidence}%" if r.confidence else "Manual"
        })

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "roll_no": student.roll_no,
            "department": student.department
        },
        "stats": {
            "total_records": total_days,
            "present": present_count,
            "late": late_count,
            "absent": absent_count,
            "attendance_rate": attendance_rate
        },
        "records": formatted_records
    }
