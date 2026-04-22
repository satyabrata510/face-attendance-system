from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from database import get_db
from models import Settings
from schemas import SettingsUpdate, SettingsResponse

router = APIRouter(prefix="/api/settings", tags=["Settings"])

# Default settings
DEFAULT_SETTINGS = {
    "face_recognition_sensitivity": "75",
    "notifications_enabled": "true",
    "low_attendance_alert": "true",
    "auto_refresh_interval": "5",
    "email_notifications": "false"
}


def get_setting_value(db: Session, key: str) -> str:
    """Get a setting value from database or return default."""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if setting:
        return setting.value
    return DEFAULT_SETTINGS.get(key, "")


def set_setting_value(db: Session, key: str, value: str):
    """Set a setting value in the database."""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Settings(key=key, value=value)
        db.add(setting)
    db.commit()


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Get all settings."""
    return SettingsResponse(
        face_recognition_sensitivity=int(get_setting_value(db, "face_recognition_sensitivity")),
        notifications_enabled=get_setting_value(db, "notifications_enabled") == "true",
        low_attendance_alert=get_setting_value(db, "low_attendance_alert") == "true",
        auto_refresh_interval=int(get_setting_value(db, "auto_refresh_interval")),
        email_notifications=get_setting_value(db, "email_notifications") == "true"
    )


@router.put("", response_model=SettingsResponse)
def update_settings(settings: SettingsUpdate, db: Session = Depends(get_db)):
    """Update settings."""
    if settings.face_recognition_sensitivity is not None:
        set_setting_value(db, "face_recognition_sensitivity", str(settings.face_recognition_sensitivity))
    
    if settings.notifications_enabled is not None:
        set_setting_value(db, "notifications_enabled", "true" if settings.notifications_enabled else "false")
    
    if settings.low_attendance_alert is not None:
        set_setting_value(db, "low_attendance_alert", "true" if settings.low_attendance_alert else "false")
    
    if settings.auto_refresh_interval is not None:
        set_setting_value(db, "auto_refresh_interval", str(settings.auto_refresh_interval))
    
    if settings.email_notifications is not None:
        set_setting_value(db, "email_notifications", "true" if settings.email_notifications else "false")
    
    # Return updated settings
    return get_settings(db)


@router.post("/reset")
def reset_settings(db: Session = Depends(get_db)):
    """Reset all settings to defaults."""
    for key, value in DEFAULT_SETTINGS.items():
        set_setting_value(db, key, value)
    
    return {"message": "Settings reset to defaults"}
