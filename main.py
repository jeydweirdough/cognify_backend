import json
import uvicorn
from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, auth
import pyrebase
from models import SignUpSchema, LoginSchema
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    description="Cognify backend API",
    title="Cognify API",
    docs_url="/"
)

# CRITICAL: Add SessionMiddleware FIRST with a strong secret key
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "change-this-to-a-random-secret-key-at-least-32-characters-long"),
    session_cookie="cognify_session",
    max_age=1800,  # 30 minutes
    same_site="lax",
    https_only=False  # Set True in production with HTTPS
)

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))  # string → dict
    else:
        # fallback to local file for local dev
        cred = credentials.Certificate("serviceAccountKey.json")

    firebase_admin.initialize_app(cred)

# Initialize Pyrebase
firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": "710951525049",
    "appId": "1:710951525049:web:ee22baa4dd865df8a89968",
    "measurementId": "G-Q62CJJZRNQ",
    "databaseURL": ""
}
pyrebase_app = pyrebase.initialize_app(firebaseConfig)
pyrebase_auth = pyrebase_app.auth()

# Configure OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.post("/signup")
async def signup_page(user_data: SignUpSchema):
    email = user_data.email
    password = user_data.password

    try:
        user = auth.create_user(email=email, password=password)
        return JSONResponse(
            content={"message": f"Successfully created user: {user.uid}"}, 
            status_code=201
        )
    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=400,
            detail=f"Account with email {email} already exists."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/login")
async def login_page(user_data: LoginSchema):
    email = user_data.email
    password = user_data.password

    try:
        user = pyrebase_auth.sign_in_with_email_and_password(email, password)
        token = user["idToken"]
        return JSONResponse(
            content={"token": token, "message": "Successfully logged in."}, 
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid email or password.")

@app.post("/logout")
async def logout_page(request: Request):
    try:
        jwt = request.headers.get("authorization")
        if jwt:
            user = auth.verify_id_token(jwt)
            auth.revoke_refresh_tokens(user['uid'])
            return JSONResponse(
                content={"message": "Successfully logged out. Please delete the token on client side."},
                status_code=200
            )
        else:
            raise HTTPException(status_code=401, detail="No authorization token provided")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/ping")
async def ping_page(request: Request):
    jwt = request.headers.get("authorization")
    try:
        user = auth.verify_id_token(jwt)
        return JSONResponse(content={"uid": user["uid"]}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get('/login/google')
async def login_via_google(request: Request):
    """Initiates Google OAuth flow"""
    try:
        redirect_uri = request.url_for('auth_callback')
        print(f"\n🔵 Starting Google OAuth")
        print(f"Redirect URI: {redirect_uri}")
        print(f"Has cookies: {bool(request.cookies)}")
        
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        print(f"❌ OAuth init error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate Google login: {str(e)}")

@app.get('/auth/callback')
async def auth_callback(request: Request):
    """Handles Google OAuth callback"""
    try:
        print(f"\n🟢 Callback received")
        print(f"Query params: {request.query_params}")
        print(f"Has cookies: {bool(request.cookies)}")
        print(f"Cookie names: {list(request.cookies.keys())}")
        
        # Try to get token
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        print(f"✅ Got user info: {email}")
        
        # Firebase operations
        try:
            user = auth.get_user_by_email(email)
            if not user.display_name and name:
                auth.update_user(user.uid, display_name=name, photo_url=picture)
        except auth.UserNotFoundError:
            user = auth.create_user(
                email=email,
                display_name=name,
                photo_url=picture,
                email_verified=True
            )
        
        # Create Firebase token
        custom_token = auth.create_custom_token(user.uid)
        user_credentials = pyrebase_auth.sign_in_with_custom_token(custom_token.decode())
        id_token = user_credentials['idToken']
        refresh_token = user_credentials.get('refreshToken', '')
        
        print(f"✅ Token generated for: {user.uid}\n")
        
        return JSONResponse(
            content={
                "token": id_token,
                "refreshToken": refresh_token,
                "email": email,
                "displayName": name,
                "photoUrl": picture,
                "uid": user.uid,
                "message": "Google login successful"
            },
            status_code=200
        )
        
    except Exception as e:
        print(f"❌ Callback error: {str(e)}\n")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

if __name__ == "__main__":    
    uvicorn.run(
        app="main:app",
        host="localhost",
        port=8000,
        reload=True
    )