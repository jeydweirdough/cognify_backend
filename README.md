# Cognify API

FastAPI backend with Firebase Authentication and Google OAuth.

This backend serves two frontend applications:

- **Web App (Admin/Faculty):** A dashboard built with TypeScript, React, and ShadCN UI.  
- **Mobile App (Student):** A mobile application built with React Native and TypeScript.

---

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
```

Fix any issues before proceeding.

### 2. Start Server

```bash
uvicorn main:app --port 8000 --reload
```

or

```bash
python main.py
```

**API:** http://localhost:8000

---

## 📘 API Endpoint Guide

This guide details the available API endpoints, their intended clients, and required roles.

---

## 🔐 Authentication (/auth)

Handles user registration, login, and token management.

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /auth/signup | Mobile | Public | (Student Only) Registers a new student account. |
| POST | /auth/login | Both | Public | Logs in any user (student, faculty, admin). |
| POST | /auth/logout | Both | Public | Clears the refresh token cookie. |
| POST | /auth/refresh | Both | Public | Gets a new ID token using the refresh token. |

### POST /auth/signup
**Sample Request Body (SignUpSchema):**
```json
{ "email": "student@example.com", "password": "strongpassword123" }
```

### POST /auth/login
**Sample Request Body (LoginSchema):**
```json
{ "email": "student@example.com", "password": "strongpassword123" }
```

**Sample Success Response:**
```json
{ "token": "ey...", "refresh_token": "ey...", "message": "Login successful" }
```

---

## 👤 User Profiles (/profiles)

Handles all operations related to user profile data.

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| GET | /all | Web | Admin, Faculty | Gets a list of all user profiles. |
| GET | / | Both | Student, Faculty, Admin | Gets the personal profile of the authenticated user. |
| POST | / | Web | Admin | Creates a new user (any role) with a password. |
| GET | /{user_id} | Web | Admin, Faculty | Gets the profile for a specific user. |
| PUT | /{user_id} | Both | Student, Faculty, Admin | Updates a user's profile. (Users can update their own). |
| DELETE | /{user_id} | Web | Admin | Soft-deletes a user profile. |
| POST | /register_device | Mobile | Student | Registers the mobile app's FCM token for push notifications. |

**Sample Payloads and Responses** are included in the source documentation.

---

## 📊 Analytics & AI (/analytics)

Endpoints for retrieving AI-generated predictions and reports.

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| GET | /global_predictions | Web | Admin, Faculty | Gets the dashboard summary of pass/fail predictions for all students. |
| GET | /student_report/{user_id} | Both | Student, Faculty, Admin | Gets detailed analytics and AI report for a student. |

**Sample Success Response:**
```json
{
  "student_id": "stu_001",
  "summary": { "total_activities": 22, "overall_score": 78.5, "time_spent_sec": 54321 },
  "prediction": { "predicted_to_pass": true, "pass_probability": 82.15 }
}
```

---

## ⚙️ Utilities (/utilities)

Endpoints for motivations and sending push notifications.

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /motivation/generate/{user_id} | Mobile | Student | Generates a new AI motivational quote. |
| GET | /motivation/{user_id} | Both | Student, Faculty, Admin | Gets the current motivational quote. |
| PUT | /motivation/{user_id} | Web | Admin, Faculty | Sets or overrides a student's motivation. |
| DELETE | /motivation/{user_id} | Web | Admin, Faculty | Clears custom motivation. |
| POST | /send_reminder/{user_id} | Web | Admin, Faculty | Sends a study reminder via push notification. |

---

## 📚 Learning Content (Modules, Quizzes, Assessments)

CRUD endpoints for managing learning content.

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /modules/upload | Web | Admin, Faculty | Uploads a module file (PDF, etc.) and returns a URL. |
| GET | /modules/ | Both | Student, Faculty, Admin | Lists all non-deleted learning modules. |
| GET | /modules/{id} | Both | Student, Faculty, Admin | Gets a single module by ID. |
| POST | /modules/ | Web | Admin, Faculty | Creates a new module. |
| PUT | /modules/{id} | Web | Admin, Faculty | Updates an existing module. |
| DELETE | /modules/{id} | Web | Admin, Faculty | Soft-deletes a module. |

**Sample Upload Response:**
```json
{ "file_url": "https://storage.googleapis.com/your-bucket/modules/12345-abc.pdf" }
```

---

## 🎓 Student Data (Activities, Recommendations)

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /recommendations/generate/{student_id} | Mobile | Student | Generates and saves new recommendations. |
| GET | /recommendations/ | Both | Student, Faculty, Admin | Lists all recommendations. |
| GET | /activities/ | Both | Student, Faculty, Admin | Lists all activities. |
| POST | /activities/ | Web | Admin, Faculty | Creates a new activity log. |

---

## 🧩 Course Structure (Subjects, TOS)

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /subjects/ | Web | Admin, Faculty | Creates a new subject. |
| GET | /subjects/{subject_id} | Web | Admin, Faculty | Gets a subject by ID. |
| POST | /subjects/{subject_id}/activate_tos/{tos_id} | Web | Admin, Faculty | Activates a TOS version for a subject. |
| GET | /tos/by_subject/{subject_id} | Both | Student, Faculty, Admin | Lists all TOS versions for a subject. |
| GET | /tos/{id} | Both | Student, Faculty, Admin | Gets a TOS document by ID. |
| POST | /tos/ | Web | Admin, Faculty | Creates a new TOS document. |

---

## 🧪 Test Data Management

The project includes tools for managing test data in Firestore.

### Generate Test Data
```bash
python -m test.cli populate
```

This creates:
- Test students with randomized profiles  
- Sample modules and activities  
- Test assessments and quizzes  
- Recommendations based on TOS mappings  

### Cleanup Test Data
```bash
python -m test.cli cleanup
```
Safely removes all test documents (prefixed with `test_`) from all collections.
