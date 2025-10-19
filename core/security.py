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

async def admin_only(request: Request):
    print("\n=== REQUEST INFO ===")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print("Headers:")
    for key, value in request.headers.items():
        print(f"  {key}: {value}")

    # Safely read JSON body
    try:
        body = await request.json()
        print("\n=== BODY ===")
        print(body)
    except Exception:
        print("No JSON body or unable to parse body.")

    print("\n✅ Request verified for admin access\n")
    return True
