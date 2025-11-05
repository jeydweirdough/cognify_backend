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
# or
python main.py
```

**API:** [http://localhost:8000](http://localhost:8000)

---

## 🔐 Authentication (/auth)

Handles user registration, login, and token management.

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /auth/signup | Mobile | Public | (Student Only) Registers a new student account. |
| POST | /auth/login | Both | Public | Logs in any user (student, faculty, admin). |
| POST | /auth/logout | Both | Public | Clears the refresh token cookie. |
| POST | /auth/refresh | Both | Public | Gets a new ID token using the refresh token. |

**Sample Sign Up Request**
```json
{
  "email": "student@example.com",
  "password": "strongpassword123"
}
```

**Sample Login Request**
```json
{
  "email": "student@example.com",
  "password": "strongpassword123"
}
```

**Success Response**
```json
{
  "token": "ey...",
  "refresh_token": "ey...",
  "message": "Login successful"
}
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
| PUT | /{user_id} | Both | Student, Faculty, Admin | Updates a user's profile. |
| DELETE | /{user_id} | Web | Admin | Soft-deletes a user profile. |
| POST | /register_device | Mobile | Student | Registers the mobile app's FCM token. |

**Example: Admin Create User**
```json
{
  "email": "faculty_member@example.com",
  "password": "newpassword123",
  "first_name": "Juan",
  "last_name": "Dela Cruz",
  "role_id": "Tzc78QtZcaVbzFtpHoOL"
}
```

---

## 📊 Analytics & AI (/analytics)

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| GET | /global_predictions | Web | Admin, Faculty | Dashboard summary of predictions. |
| GET | /student_report/{user_id} | Both | Student, Faculty, Admin | Detailed analytics for a student. |

**Sample Response**
```json
{
  "student_id": "stu_001",
  "summary": {
    "total_activities": 22,
    "overall_score": 78.5,
    "time_spent_sec": 54321
  },
  "prediction": {
    "predicted_to_pass": true,
    "pass_probability": 82.15
  }
}
```

---

## 🛠 Utilities (/utilities)

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /motivation/generate/{user_id} | Mobile | Student | Generates new AI motivational quote. |
| GET | /motivation/{user_id} | Both | All | Gets saved motivational quote. |
| PUT | /motivation/{user_id} | Web | Admin, Faculty | Sets custom motivation. |
| DELETE | /motivation/{user_id} | Web | Admin, Faculty | Clears custom motivation. |
| POST | /send_reminder/{user_id} | Web | Admin, Faculty | Sends study reminder push notification. |

---

## 📚 Learning Content (Modules, Quizzes, Assessments)

CRUD endpoints for managing learning content such as modules, quizzes, and assessments.

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| GET | /modules/ | Both | All | Lists all modules. |
| GET | /modules/{id} | Both | All | Gets a module by ID. |
| POST | /modules/ | Web | Admin, Faculty | Creates a new module. |
| PUT | /modules/{id} | Web | Admin, Faculty | Updates an existing module. |
| DELETE | /modules/{id} | Web | Admin, Faculty | Soft-deletes a module. |

---

## 🧠 Student Data (/recommendations, /activities)

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /recommendations/generate/{student_id} | Mobile | Student | Generates recommendations. |
| GET | /recommendations/ | Both | All | Lists all recommendations. |
| GET | /activities/ | Both | All | Lists all activities. |
| POST | /activities/ | Web | Admin, Faculty | Creates a new activity log. |

---

## 📘 Course Structure (Subjects, TOS)

| Method | Path | Client | Role | Description |
|--------|------|---------|------|--------------|
| POST | /subjects/ | Web | Admin, Faculty | Creates a new subject. |
| GET | /subjects/{subject_id} | Web | Admin, Faculty | Gets subject by ID. |
| POST | /subjects/{subject_id}/activate_tos/{tos_id} | Web | Admin, Faculty | Activates a TOS version. |
| GET | /tos/by_subject/{subject_id} | Both | All | Lists TOS versions for subject. |
| POST | /tos/ | Web | Admin, Faculty | Creates new TOS document. |

---

## 🧩 Test Data Management

### Generate Test Data
```bash
python -m test.cli populate
```

Creates:
- Test students
- Sample modules & activities
- Assessments & quizzes
- Recommendations

### Cleanup Test Data
```bash
python -m test.cli cleanup
```

Removes all test documents from Firestore (prefixed with `test_`).
