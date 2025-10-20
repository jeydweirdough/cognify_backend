from fastapi import Depends, HTTPException, Request, status
from firebase_admin import auth
from database.firestore import db

def verify_firebase_token(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    try:
        token = auth_header.split(" ")[1]
        return auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def admin_only(decoded_token: dict = Depends(verify_firebase_token)):
    """
    Restricts access to users whose Firestore role document
    contains designation == 'admin'.
    """
    uid = decoded_token.get("uid")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_doc = db.collection("user_profiles").document(uid).get()
        role_id = user_doc.to_dict().get("role_id")

        role_doc = db.collection("roles").document(role_id).get()
        if not role_doc.exists:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role is not set properly")

        role_data = role_doc.to_dict()
        if role_data.get("designation") != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access only")

        return decoded_token  # success → pass user data onward

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))