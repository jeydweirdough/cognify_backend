# Cognify API

FastAPI backend with Firebase Authentication, AI-powered content generation, and predictive analytics.

This backend serves two frontend applications:

- **Web App (Admin/Faculty):** A dashboard built with TypeScript, React, and ShadCN UI.
- **Mobile App (Student):** A mobile application built with React Native and TypeScript.

---

## 🚀 Quick Setup

### 1. Install Dependencies

You must have Python 3.10 or newer.

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install main dependencies
# (Includes new 'pymupdf' for PDF reading and 'httpx' for AI service)
pip install -r requirements.txt

> **Note:** `requirements.txt` includes `pymupdf` for PDF reading and `httpx` for the AI service, which are crucial for the new AI features.

### 2. Start Server

```bash
uvicorn main:app --port 8000 --reload
```

or

```bash
python main.py
```

**API:** [http://localhost:8000](http://localhost:8000)

---

## 📘 API Endpoint Guide

### A Note on Pagination

All API endpoints that return a list of items (e.g., `GET /modules/`, `GET /profiles/all`, `GET /activities/`) are optimized with cursor-based pagination.

To use them, include query parameters:

- `limit=INT`: (Optional, default 20) The number of items to return.
- `start_after=DOC_ID`: (Optional) The `id` of the last document from the previous page.

All paginated responses follow this consistent structure:

```json
{
  "items": [
    { "id": "doc_1", "...": "..." },
    { "id": "doc_2", "...": "..." }
  ],
  "last_doc_id": "doc_2"
}
```

---

## 🔐 Authentication (/auth)

Handles user registration, login, and token management.

| Method | Path          | Client | Role   | Description |
|--------|---------------|--------|--------|--------------|
| POST   | /auth/signup  | Mobile | Public | (Student Only) Registers a new student account. |
| POST   | /auth/login   | Both   | Public | Logs in any user (student, faculty, admin). |
| POST   | /auth/logout  | Both   | Public | Clears the refresh token cookie. |
| POST   | /auth/refresh | Both   | Public | Gets a new ID token using the refresh token. |

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
|--------|------|--------|------|--------------|
| GET | /all | Web | Admin, Faculty | Gets a **paginated** list of all user profiles. |
| GET | / | Both | Student, Faculty, Admin | Gets the personal profile of the authenticated user. |
| POST | / | Web | Admin | Creates a new user (any role) with a password. |
| GET | /{user_id} | Web | Admin, Faculty | Gets the profile for a specific user. |
| PUT | /{user_id} | Both | Student, Faculty, Admin | Updates a user's profile. (Users can update their own). |
| DELETE | /{user_id} | Web | Admin | Soft-deletes a user profile. |
| POST | /register_device | Mobile | Student | Registers the mobile app's FCM token for push notifications. |

---

## 🧠 AI Content Generation (/generate)

This is the core of the AI-powered learning system. It allows the API to read uploaded PDF modules and automatically generate new study materials aligned with the **Table of Specifications (TOS)**.

**Workflow:**

1. An Admin/Faculty uploads a PDF file using `POST /modules/upload`.
2. The admin triggers this endpoint: `POST /generate/from_module/{module_id}`.
3. The API downloads the PDF, reads its text, fetches the **Active TOS**, and sends all info to the AI.
4. The AI generates a summary, quiz, and flashcards, **all categorized by TOS topic and Bloom's Level**.
5. Students and faculty can then retrieve the new, aligned content.

| Method | Path | Client | Role | Description |
|--------|------|--------|------|--------------|
| POST | /from_module/{module_id} | Web | Admin, Faculty | **(Trigger)** Starts a background task to generate all AI content for a module, **aligned to the active TOS**. |
| GET | /generated_summaries/for_module/{module_id} | Both | All | Gets a **paginated** list of AI-generated summaries for a module. |
| GET | /generated_quizzes/for_module/{module_id} | Both | All | Gets a **paginated** list of AI-generated quizzes for a module. |
| GET | /generated_flashcards/for_module/{module_id} | Both | All | Gets a **paginated** list of AI-generated flashcard decks for a module. |

---

## 📊 Analytics & AI (/analytics)

Endpoints for retrieving AI-generated *student predictions* and *performance reports*.

| Method | Path | Client | Role | Description |
|--------|------|--------|------|--------------|
| GET | /global_predictions | Web | Admin, Faculty | Gets the dashboard summary of pass/fail predictions for all students. |
| GET | /student_report/{user_id} | Both | Student, Faculty, Admin | Gets the detailed analytics and AI prediction report for a single student. |

**Sample `/student_report/{user_id}` Response:**

```json
{
  "student_id": "stu_001",
  "summary": { "total_activities": 22, "overall_score": 78.5, "time_spent_sec": 54321 },
  "performance_by_bloom": { "remembering": 85.0, "applying": 72.0 },
  "prediction": { "predicted_to_pass": true, "pass_probability": 82.15 },
  "last_updated": "2025-10-27T03:00:00Z"
}
```

---

## ⚙️ Utilities (/utilities)

Endpoints for on-demand motivation and sending push notifications.

| Method | Path | Client | Role | Description |
|--------|------|--------|------|--------------|
| POST | /motivation/generate/{user_id} | Mobile | Student | **On-demand** generation of a new AI motivational quote based on the student's latest analytics. |
| GET | /motivation/{user_id} | Both | Student, Faculty, Admin | Gets the current motivational quote (prioritizes faculty-set, then AI). |
| PUT | /motivation/{user_id} | Web | Admin, Faculty | Sets or overrides a student's motivation. |
| DELETE | /motivation/{user_id} | Web | Admin, Faculty | Clears custom motivation, reverting to the AI-generated one. |
| POST | /send_reminder/{user_id} | Web | Admin, Faculty | Sends a study reminder via push notification. |

---

## 📚 Learning Content (Modules, Quizzes, Assessments)

CRUD endpoints for managing *manual* learning content.

| Method | Path | Client | Role | Description |
|--------|------|--------|------|--------------|
| POST | /modules/upload | Web | Admin, Faculty | **(Step 1 for AI)** Uploads a module file (PDF, etc.) and returns a URL. |
| GET | /modules/ | Both | Student, Faculty, Admin | Lists all non-deleted learning modules (supports **pagination**). |
| GET | /modules/{id} | Both | Student, Faculty, Admin | Gets a single module by ID. |
| POST | /modules/ | Web | Admin, Faculty | Creates a new module. |
| PUT | /modules/{id} | Web | Admin, Faculty | Updates an existing module. |
| DELETE | /modules/{id} | Web | Admin, Faculty | Soft-deletes a module. |
| GET | /quizzes/ | Both | All | Lists all *manual* quizzes (supports **pagination**). |
| GET | /assessments/ | Both | All | Lists all *manual* assessments (supports **pagination**). |

**Sample Upload Response:**

```json
{ "file_url": "https://storage.googleapis.com/your-bucket/modules/12345-abc.pdf" }
```

---

## 🎓 Student Data (Activities, Recommendations)

| Method | Path | Client | Role | Description |
|--------|------|--------|------|--------------|
| POST | /recommendations/generate/{student_id} | Mobile | Student | Generates and saves new module recommendations. |
| GET | /recommendations/ | Both | Student, Faculty, Admin | Lists all recommendations (supports **pagination**). |
| GET | /activities/ | Both | Student, Faculty, Admin | Lists all activities (supports **pagination**). |
| POST | /activities/ | Web | Admin, Faculty | Creates a new activity log. |

---

## 🧩 Course Structure (Subjects, TOS)

| Method | Path | Client | Role | Description |
|--------|------|--------|------|--------------|
| POST | /subjects/ | Web | Admin, Faculty | Creates a new subject. |
| GET | /subjects/{subject_id} | Web | Admin, Faculty | Gets a subject by ID. |
| POST | /subjects/{subject_id}/activate_tos/{tos_id} | Web | Admin, Faculty | Activates a TOS version for a subject. |
| GET | /tos/by_subject/{subject_id} | Both | Student, Faculty, Admin | Lists all TOS versions for a subject (supports **pagination**). |
| GET | /tos/{id} | Both | Student, Faculty, Admin | Gets a TOS document by ID. |
| POST | /tos/ | Web | Admin, Faculty | Creates a new TOS document. |

---

## 🧪 Test Data Management

The project includes tools for managing test data in Firestore.

**Generate Test Data:**

```bash
python -m test.cli populate
```

This creates:

- Test students with randomized profiles
- Sample modules and activities
- Test assessments and quizzes
- Recommendations based on TOS mappings

**Cleanup Test Data:**

```bash
python -m test.cli cleanup
```

Safely removes all test documents (prefixed with `test_`) from all collections.
