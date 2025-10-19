# Cognify API

FastAPI backend with Firebase Authentication and Google OAuth.

## Quick Setup

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

API: `http://localhost:8000`

## API Endpoints

**Auth:**
- `POST /auth/signup` - Register with email/password
- `POST /auth/login` - Login with email/password
- `POST /auth/logout` - Revoke tokens
- `POST /auth/refresh` - Refresh token

**Profiles:**
- `GET /profiles/{user_id}` - Get profile
- `POST /profiles/{user_id}` - Create profile
- `PUT /profiles/{user_id}` - Update profile
- `DELETE /profiles/{user_id}` - Delete profile

## Example Request

```bash
# Signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Pass123!","first_name":"John"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Pass123!"}'
```