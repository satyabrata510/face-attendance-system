# 📸 AI-Driven Face Recognition Attendance System

![System Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Next.js](https://img.shields.io/badge/Frontend-Next.js-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)
![Python](https://img.shields.io/badge/AI-OpenCV%20%7C%20Dlib-3776AB?logo=python)

A full-stack, secure, and touchless attendance management solution that leverages modern Deep Learning and Computer Vision techniques to automate roll calls in educational institutions and organizations.

## ✨ Key Features

- **🤖 AI Face Recognition:** Real-time, fast, and highly accurate face detection using advanced `dlib` embeddings and OpenCV.
- **📷 Live Camera Tracking:** Seamlessly process live video feeds to automatically mark attendance for registered students.
- **🛡️ Role-Based Access Control:** Secure, separate dashboards for Administrators and Teachers with branch-specific data isolation.
- **📊 Interactive Analytics:** Beautiful, responsive dashboards featuring charts and student records built with Next.js and Tailwind CSS.
- **👥 Automated Enrollment:** Instantly register students by uploading images to generate secure facial feature embeddings.
- **⚡ High Performance REST API:** A highly scalable backend powered by Python's FastAPI.

## 🛠️ Technology Stack

**Frontend:**
- Framework: `Next.js` (React)
- Styling: `Tailwind CSS`
- Language: `TypeScript`

**Backend:**
- Framework: `FastAPI`
- Face Recognition Engine: `OpenCV`, `dlib`, `face_recognition`
- Database: `SQLite`

## 🚀 Getting Started Locally

If you want to run this application on your local machine, follow these instructions:

### 1. Start the Backend server
Open a terminal and navigate to the `backend` folder:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
uvicorn main:app --reload
