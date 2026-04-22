from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
import os

import models, schemas
from database import get_db

# Secret key for JWT
SECRET_KEY = "face_detection_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def convert_dob_to_ddmmyyyy(dob_str: str) -> str:
    if not dob_str:
        return ""
    
    if "/" in dob_str:
        parts = dob_str.split("/")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return f"{parts[2].zfill(2)}{parts[1].zfill(2)}{parts[0]}"
            return f"{parts[0].zfill(2)}{parts[1].zfill(2)}{parts[2]}"
    elif "-" in dob_str:
        parts = dob_str.split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return f"{parts[2].zfill(2)}{parts[1].zfill(2)}{parts[0]}"
            return f"{parts[0].zfill(2)}{parts[1].zfill(2)}{parts[2]}"
            
    import re
    digits = re.sub(r'\D', '', dob_str)
    return digits if len(digits) == 8 else dob_str

TEACHER_CREDENTIALS = {
    "TATCSE": {"password": "CSE@123", "branch": "CSE"},
    "TATEE": {"password": "EE@123", "branch": "EE"},
    "TATCIVIL": {"password": "CIVIL@123", "branch": "CIVIL"},
    "TATMECH": {"password": "MECH@123", "branch": "MECH"}
}


@router.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Try to authenticate as Admin
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if user and verify_password(form_data.password, user.hashed_password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": f"admin:{user.username}"}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer", "role": "admin"}

    # 1.5 Try to authenticate as Teacher
    if form_data.username in TEACHER_CREDENTIALS:
        if form_data.password == TEACHER_CREDENTIALS[form_data.username]["password"]:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            branch = TEACHER_CREDENTIALS[form_data.username]["branch"]
            access_token = create_access_token(
                data={"sub": f"teacher:{form_data.username}", "branch": branch}, expires_delta=access_token_expires
            )
            return {
                "access_token": access_token, 
                "token_type": "bearer", 
                "role": "teacher",
                "branch": branch
            }

    # 2. Try to authenticate as Student (username = roll_no)
    student = db.query(models.Student).filter(models.Student.roll_no == form_data.username).first()
    
    is_student_auth = False
    
    if student:
        if student.dob:
             converted_dob = convert_dob_to_ddmmyyyy(student.dob)
             if form_data.password == converted_dob:
                 is_student_auth = True
        elif not student.dob and (form_data.password == student.roll_no or form_data.password == "Student@123"):
             # Legacy fallback if no DOB registered yet
             is_student_auth = True
                
    if is_student_auth:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": f"student:{student.roll_no}"}, expires_delta=access_token_expires
        )
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "role": "student",
            "student_id": student.id
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Registration Number or Date of Birth.",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
            
        role, username = "admin", sub
        if ":" in sub:
            role, username = sub.split(":", 1)
            
    except JWTError:
        raise credentials_exception
        
    if role == "admin":
        user = db.query(models.User).filter(models.User.username == username).first()
        if user is None:
            raise credentials_exception
        return user
    elif role == "student":
        student = db.query(models.Student).filter(models.Student.roll_no == username).first()
        if student is None:
            raise credentials_exception
            
        # Use a simple class with init to avoid scoping issues in class body
        class UserObj:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        return UserObj(
            id=student.id,
            username=student.roll_no,
            is_active=1 if student.status == "Active" else 0,
            role="student"
        )
    elif role == "teacher":
        class UserObj:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        return UserObj(
            id=9999,
            username=username,
            is_active=1,
            role="teacher",
            branch=payload.get("branch")
        )
        
    raise credentials_exception

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if current_user.is_active == 0:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/student/signup", response_model=schemas.StudentResponse)
def signup_student(student_data: schemas.StudentSignup, db: Session = Depends(get_db)):
    # Check if a student with the same roll_no already exists
    existing_student = db.query(models.Student).filter(models.Student.roll_no == student_data.roll_no).first()
    if existing_student:
        # If student exists but hasn't set a password yet, we let them "sign up" by claiming the profile
        if not existing_student.hashed_password:
            existing_student.hashed_password = get_password_hash(student_data.password)
            existing_student.name = student_data.name
            existing_student.department = student_data.department
            db.commit()
            db.refresh(existing_student)
            return existing_student
        else:
            raise HTTPException(status_code=400, detail="Student with this Roll No is already registered.")

    # Prevent creating new student profiles explicitly
    raise HTTPException(
        status_code=403, 
        detail="Access Denied: Your Roll No is not assigned in the system. Please ask the Admin to import your details first."
    )
