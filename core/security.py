from fastapi import Request, Depends, HTTPException, status
from firebase_admin import auth
from core.firebase import db
import asyncio

async def get_user_role(uid: str) -> str:
    """Fetch the user's role (designation) from Firestore."""
    def _fetch_role():
        user_doc = db.collection("user_profiles").document(uid).get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User profile not found")

        role_id = user_doc.to_dict().get("role_id")
        if not role_id:
            raise HTTPException(status_code=403, detail="User role not assigned")

        role_doc = db.collection("roles").document(role_id).get()
        if not role_doc.exists:
            raise HTTPException(status_code=403, detail="Role not found")

        return role_doc.to_dict().get("designation", "").lower()

    return await asyncio.to_thread(_fetch_role)


def verify_firebase_token(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    try:
        token = auth_header.split(" ")[1]
        return auth.verify_id_token(token)
    except Exception as e:
        print(f"Error verifying Firebase token: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def allowed_users(roles: list[str]):
    """
    Shortcut dependency to allow only specified roles.
    Admin always has full access automatically.
    Supports self-access for non-admin users.
    """
    async def dependency(
        decoded: dict = Depends(verify_firebase_token),
        request: Request = None,
        user_id: str = None  # route parameter for self-access
    ):
        uid = decoded["uid"]

        # Get user role
        role = await get_user_role(uid)
        decoded["role"] = role

        # Admin bypass
        if role == "admin":
            return decoded

        # Role check
        if role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' cannot access this resource."
            )

        # Self-access check
        if user_id and uid != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own resource"
            )

        return decoded

    return dependency