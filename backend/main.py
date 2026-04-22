from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database import engine, Base, SessionLocal
from routers import students, attendance, reports, settings, auth
import models
from routers.auth import get_password_hash

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Face Recognition Attendance System",
    description="Backend API for face recognition based attendance management",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
os.makedirs("uploads", exist_ok=True)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(reports.router)
app.include_router(settings.router)

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    admin_user = db.query(models.User).filter(models.User.username == "Satya01").first()
    if not admin_user:
        hashed_password = get_password_hash("Satya@123")
        new_admin = models.User(username="Satya01", hashed_password=hashed_password)
        db.add(new_admin)
        db.commit()
    
    super_admin = db.query(models.User).filter(models.User.username == "ADMIN").first()
    if not super_admin:
        hashed_password = get_password_hash("ADMIN@123")
        new_super_admin = models.User(username="ADMIN", hashed_password=hashed_password)
        db.add(new_super_admin)
        db.commit()
    db.close()


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Face Recognition Attendance System API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/auth",
            "students": "/api/students",
            "attendance": "/api/attendance",
            "reports": "/api/reports",
            "settings": "/api/settings"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
