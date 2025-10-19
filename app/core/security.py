from fastapi import HTTPException, Request
from firebase_admin import auth

def verify_firebase_token(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    try:
        token = auth_header.split(" ")[1]
        return auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
