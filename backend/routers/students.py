from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import os
from datetime import datetime

from database import get_db
import models
from models import Student
from schemas import (
    StudentCreate, 
    StudentUpdate, 
    StudentResponse, 
    StudentListResponse,
    StudentImportResponse,
    FaceRegistrationResponse
)
from services.face_recognition_service import face_service
from routers.auth import get_current_active_user

router = APIRouter(prefix="/api/students", tags=["Students"])

UPLOAD_DIR = "uploads"


@router.get("", response_model=StudentListResponse)
def get_students(
    search: str = None,
    department: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_active_user)
):
    """Get all students with optional filters."""
    query = db.query(Student)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Student.name.ilike(search_filter)) |
            (Student.roll_no.ilike(search_filter)) |
            (Student.department.ilike(search_filter))
        )
    
    if department:
        query = query.filter(Student.department == department)
    
    if status:
        query = query.filter(Student.status == status)
        
    # Filter by branch if teacher
    if hasattr(current_user, "role") and current_user.role == "teacher" and hasattr(current_user, "branch") and current_user.branch:
        teacher_branch = current_user.branch.strip().upper()
        query = query.filter(func.upper(Student.department) == teacher_branch)
    
    students = query.all()
    
    student_responses = [
        StudentResponse(
            id=s.id,
            name=s.name,
            roll_no=s.roll_no,
            department=s.department,
            status=s.status,
            dob=s.dob,
            photo_url=s.photo_url,
            face_image_url=f"/{s.face_image_path}".replace("\\", "/") if s.face_image_path else None,
            has_face_registered=s.face_encoding is not None,
            created_at=s.created_at
        )
        for s in students
    ]
    
    return StudentListResponse(students=student_responses, total=len(students))


@router.post("", response_model=StudentResponse)
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    """Create a new student."""
    # Check if roll number already exists
    existing = db.query(Student).filter(Student.roll_no == student.roll_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="Roll number already exists")
    
    db_student = Student(
        name=student.name,
        roll_no=student.roll_no,
        department=student.department,
        dob=student.dob,
        photo_url=student.photo_url
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    
    return StudentResponse(
        id=db_student.id,
        name=db_student.name,
        roll_no=db_student.roll_no,
        department=db_student.department,
        status=db_student.status,
        dob=db_student.dob,
        photo_url=db_student.photo_url,
        face_image_url=f"/{db_student.face_image_path}".replace("\\", "/") if db_student.face_image_path else None,
        has_face_registered=False,
        created_at=db_student.created_at
    )


import pandas as pd
import io
import requests
import re
import uuid

def process_google_drive_link(url: str):
    """Extract ID from Google Drive URL and download it."""
    if not url: return None
    
    match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if not match:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    
    if match:
        file_id = match.group(1)
        # Google Drive direct download link
        download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
        try:
            response = requests.get(download_url, timeout=15)
            if response.status_code == 200 and 'text/html' not in response.headers.get('Content-Type', ''):
                return response.content
        except Exception as e:
            print(f"DEBUG: Error downloading from Drive: {e}")
    else:
        # direct URL fallback
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200 and 'text/html' not in response.headers.get('Content-Type', ''):
                return response.content
        except Exception as e:
            print(f"DEBUG: Error downloading direct URL: {e}")
    
    return None

@router.post("/import", response_model=StudentImportResponse)
async def import_students(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """A highly relaxed student import endpoint to prevent unnecessary row skipping."""
    print(f"DEBUG: Starting Relaxed Import for file: {file.filename}")
    is_excel = file.filename.endswith(('.xlsx', '.xls', '.xlsm', '.xlsb', '.XLSX', '.XLS'))
    is_csv = file.filename.endswith(('.csv', '.CSV'))
    
    if not (is_excel or is_csv):
        print(f"DEBUG: Unsupported file format: {file.filename}")
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    try:
        contents = await file.read()
        if is_excel:
            full_df = pd.read_excel(io.BytesIO(contents), header=None)
        else:
            full_df = pd.read_csv(io.BytesIO(contents), header=None, on_bad_lines='skip')
            
        print(f"DEBUG: Total rows read from file: {len(full_df)}")
        
        # 1. FIND THE HEADER ROW (looking for "Name" and "Reg no.")
        header_row_idx = 0
        for r_idx, row in full_df.iterrows():
            row_vals = [str(val).strip() for val in row.values if pd.notna(val)]
            if any("Name" == v for v in row_vals) or any("Reg no." == v for v in row_vals):
                header_row_idx = r_idx
                print(f"DEBUG: Found header at row {r_idx}")
                break
        
        # Prepare the dataframe
        df = full_df.iloc[header_row_idx+1:].reset_index(drop=True)
        df.columns = [str(c).strip() if pd.notna(c) else f"unnamed_{i}" for i, c in enumerate(full_df.iloc[header_row_idx])]
        
        # Exact Mapping as per user request
        name_col = "Name" if "Name" in df.columns else None
        reg_col = "Reg no." if "Reg no." in df.columns else None
        dob_col = "DOB" if "DOB" in df.columns else None
        branch_col = "Branch" if "Branch" in df.columns else None
        
        # Enhanced photo column detection
        photo_col = None
        photo_aliases = ["Photo", "Photo Link", "Photo URL", "Photos", "Image", "Image Link", "Image URL"]
        for col in df.columns:
            if str(col).strip().title() in [alias.title() for alias in photo_aliases]:
                photo_col = col
                break
        
        print(f"DEBUG: Using Columns -> Name: {name_col}, Reg: {reg_col}, DOB: {dob_col}, Branch: {branch_col}, Photo: {photo_col}")
        
        imported_count = 0
        failed_count = 0
        
        # 2. PROCESS ROWS (RELAXED VALIDATION)
        for idx, row in df.iterrows():
            # Skip completely empty rows
            if row.isna().all() or (row.fillna('').astype(str).str.strip() == '').all():
                continue
                
            print(f"DEBUG: Processing Row {idx}: {row.to_dict()}")
            
            try:
                # Extract and Trim
                raw_name = row.get(name_col)
                name = str(raw_name).strip() if pd.notna(raw_name) else ""
                
                raw_reg = row.get(reg_col)
                # CRITICAL: Always convert registrationNumber to string
                reg_no = str(raw_reg).strip() if pd.notna(raw_reg) else ""
                if reg_no.endswith('.0'): reg_no = reg_no[:-2] # Cleanup Excel float artifacts
                
                raw_branch = row.get(branch_col)
                branch = str(raw_branch).strip() if pd.notna(raw_branch) else ""
                
                raw_dob = row.get(dob_col)
                dob_raw = raw_dob
                
                raw_photo = row.get(photo_col)
                photo = str(raw_photo).strip() if pd.notna(raw_photo) else None
                
                # RELAXED VALIDATION: Only name and reg_no must exist
                if not name or name.lower() == 'nan':
                    print(f"DEBUG: Skipping Row {idx}: Missing Name")
                    failed_count += 1
                    continue
                if not reg_no or reg_no.lower() == 'nan':
                    print(f"DEBUG: Skipping Row {idx}: Missing Reg no.")
                    failed_count += 1
                    continue
                
                # DOB HANDLING: Serial dates or strings
                dob_str = None
                if pd.notna(dob_raw):
                    try:
                        # pd.to_datetime handles strings and serial numbers automatically
                        dob_dt = pd.to_datetime(dob_raw)
                        dob_str = dob_dt.strftime('%Y-%m-%d')
                    except Exception:
                        # Fallback: if it's a string use it as is or try simple conversion
                        dob_str = str(dob_raw).strip()
                
                # DUPLICATE CHECK: Skip if already in DB
                existing = db.query(Student).filter(Student.roll_no == reg_no).first()
                if existing:
                    print(f"DEBUG: Skipping Row {idx}: Reg no. '{reg_no}' already exists in database")
                    failed_count += 1
                    continue
                
                # Insert row
                new_student = Student(
                    name=name,
                    roll_no=reg_no,
                    department=branch if branch.lower() != 'nan' else "",
                    dob=dob_str if dob_str and dob_str.lower() != 'nan' else None,
                    photo_url=photo if photo and photo.lower() != 'nan' else None,
                    status="Active"
                )
                db.add(new_student)
                db.flush()
                
                # --- PHOTO EXTRACTION & ENCODING ---
                if new_student.photo_url:
                    print(f"DEBUG: Fetching photo link for {new_student.name}...")
                    image_bytes = process_google_drive_link(new_student.photo_url)
                    if image_bytes:
                        is_valid, _ = face_service.validate_face_image(image_bytes)
                        if is_valid:
                            face_encoding = face_service.encode_face(image_bytes)
                            if face_encoding is not None:
                                os.makedirs(UPLOAD_DIR, exist_ok=True)
                                unique_filename = f"student_{new_student.id}_{uuid.uuid4().hex[:8]}.jpg"
                                file_path = os.path.join(UPLOAD_DIR, unique_filename)
                                with open(file_path, "wb") as f:
                                    f.write(image_bytes)
                                
                                new_student.face_encoding = face_encoding
                                new_student.face_image_path = file_path
                                print(f"DEBUG: Successfully encoded face for {new_student.name}")
                            else:
                                print(f"DEBUG: Face encoding computation failed for {new_student.name}")
                        else:
                            print(f"DEBUG: Invalid face detected for {new_student.name}")
                    else:
                        print(f"DEBUG: Failed to download photo for {new_student.name} - make sure link is public")
                # -----------------------------------
                
                imported_count += 1
                
            except Exception as e_row:
                db.rollback()
                print(f"DEBUG: Row {idx} Failed with Error: {str(e_row)}")
                failed_count += 1
                
        db.commit()
        print(f"DEBUG: Final Count -> Imported: {imported_count}, Failed: {failed_count}")
        
        msg = f"{imported_count} students imported successfully"
        return StudentImportResponse(
            success=True,
            imported_count=imported_count,
            failed_count=failed_count,
            message=msg
        )
        
    except Exception as e_master:
        print(f"CRITICAL ERROR: {str(e_master)}")
        return StudentImportResponse(
            success=False,
            imported_count=0,
            failed_count=0,
            message=f"Import failed: {str(e_master)}"
        )

    except Exception as e:
        return StudentImportResponse(
            success=False,
            imported_count=0,
            failed_count=0,
            message=str(e)
        )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    """Get a specific student by ID."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return StudentResponse(
        id=student.id,
        name=student.name,
        roll_no=student.roll_no,
        department=student.department,
        status=student.status,
        dob=student.dob,
        photo_url=student.photo_url,
        face_image_url=f"/{student.face_image_path}".replace("\\", "/") if student.face_image_path else None,
        has_face_registered=student.face_encoding is not None,
        created_at=student.created_at
    )


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int, 
    student_update: StudentUpdate, 
    db: Session = Depends(get_db)
):
    """Update a student's information."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check roll number uniqueness if being updated
    if student_update.roll_no and student_update.roll_no != student.roll_no:
        existing = db.query(Student).filter(Student.roll_no == student_update.roll_no).first()
        if existing:
            raise HTTPException(status_code=400, detail="Roll number already exists")
    
    # Update fields
    update_data = student_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)
    
    db.commit()
    db.refresh(student)
    
    return StudentResponse(
        id=student.id,
        name=student.name,
        roll_no=student.roll_no,
        department=student.department,
        status=student.status,
        dob=student.dob,
        photo_url=student.photo_url,
        face_image_url=f"/{student.face_image_path}".replace("\\", "/") if student.face_image_path else None,
        has_face_registered=student.face_encoding is not None,
        created_at=student.created_at
    )


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    """Delete a student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Delete face image if exists
    if student.face_image_path and os.path.exists(student.face_image_path):
        os.remove(student.face_image_path)
    
    # Delete associated attendance records to avoid foreign key constraint errors
    db.query(models.Attendance).filter(models.Attendance.student_id == student_id).delete()
    
    db.delete(student)
    db.commit()
    
    return {"message": "Student deleted successfully"}


@router.post("/{student_id}/face", response_model=FaceRegistrationResponse)
async def register_face(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Register a face for a student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Read image bytes
    image_bytes = await file.read()
    
    # Validate the image
    is_valid, message = face_service.validate_face_image(image_bytes)
    if not is_valid:
        return FaceRegistrationResponse(
            success=False,
            message=message,
            student_id=student_id
        )
    
    # Encode the face
    face_encoding = face_service.encode_face(image_bytes)
    if face_encoding is None:
        return FaceRegistrationResponse(
            success=False,
            message="Failed to encode face. Please try with a clearer image.",
            student_id=student_id
        )
    
    # Save the image
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"student_{student_id}.jpg")
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    
    # Update student record
    student.face_encoding = face_encoding
    student.face_image_path = file_path
    db.commit()
    
    return FaceRegistrationResponse(
        success=True,
        message="Face registered successfully",
        student_id=student_id
    )
