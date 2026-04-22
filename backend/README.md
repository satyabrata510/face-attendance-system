# Face Recognition Attendance System - Backend

A Python FastAPI backend for the face recognition based attendance management system.

## Features

- **Student Management**: CRUD operations for students
- **Face Registration**: Register student faces for recognition
- **Attendance Marking**: Mark attendance using face recognition
- **Reports & Analytics**: Dashboard statistics, weekly/monthly trends
- **Settings Management**: Configure recognition sensitivity and notifications

## Prerequisites

- Python 3.9+
- CMake (required for dlib/face_recognition)
  - macOS: `brew install cmake`
  - Ubuntu: `sudo apt-get install cmake`

## Installation

1. **Create virtual environment**
   ```bash
   cd face-detection-be
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --port 8000

# Or run directly
python main.py
```

The API will be available at:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Students
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/students` | List all students |
| POST | `/api/students` | Create new student |
| GET | `/api/students/{id}` | Get student details |
| PUT | `/api/students/{id}` | Update student |
| DELETE | `/api/students/{id}` | Delete student |
| POST | `/api/students/{id}/face` | Register face |

### Attendance
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/attendance/mark` | Mark via face recognition |
| POST | `/api/attendance/mark/{id}` | Manual marking |
| GET | `/api/attendance/today` | Today's attendance |
| GET | `/api/attendance/recent` | Recent activity |
| GET | `/api/attendance/{date}` | Attendance by date |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/dashboard` | Dashboard stats |
| GET | `/api/reports/weekly` | Weekly trend |
| GET | `/api/reports/monthly` | Monthly trend |
| GET | `/api/reports/department` | Department stats |
| GET | `/api/reports/export/csv` | Export CSV |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get settings |
| PUT | `/api/settings` | Update settings |
| POST | `/api/settings/reset` | Reset to defaults |

## Project Structure

```
face-detection-be/
├── main.py                 # FastAPI application entry
├── database.py             # Database configuration
├── models.py               # SQLAlchemy models
├── schemas.py              # Pydantic schemas
├── requirements.txt        # Python dependencies
├── routers/
│   ├── students.py         # Student endpoints
│   ├── attendance.py       # Attendance endpoints
│   ├── reports.py          # Reports endpoints
│   └── settings.py         # Settings endpoints
├── services/
│   └── face_recognition_service.py
└── uploads/                # Face images storage
```

## License

MIT
