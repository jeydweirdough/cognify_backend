import importlib
import os
import sys
import socket
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi.testclient import TestClient
import requests

print("=============================================")
print("🚀  COGNIFY FASTAPI BACKEND DIAGNOSTICS")
print("=============================================")

# === SETUP PATHS ===
BASE_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BASE_DIR / "app"
sys.path.append(str(BASE_DIR))

# === LOAD ENVIRONMENT VARIABLES ===
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
else:
    print("⚠️  .env file not found")

# === CHECK REQUIRED MODULES ===
required_modules = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "firebase_admin": "firebase_admin",
    "python-dotenv": "dotenv",
    "pydantic": "pydantic",
    "requests": "requests",
    "itsdangerous": "itsdangerous"
}

print("\n📦 Checking dependencies...")
for mod in required_modules:
    try:
        importlib.import_module(mod)
        print(f"✅ {mod} installed")
    except ImportError:
        print(f"❌ {mod} missing — install it using: pip install {mod}")

# === CHECK FIREBASE CONFIGURATION ===
firebase_key = BASE_DIR / "serviceAccountKey.json"
print("\n🔥 Checking Firebase configuration...")
if firebase_key.exists():
    print(f"✅ Firebase key found: {firebase_key}")
    try:
        import firebase_admin
        from firebase_admin import credentials, auth

        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_key)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully")
        else:
            print("ℹ️  Firebase already initialized")

        project_id = os.getenv("FIREBASE_PROJECT_ID", None)
        if project_id:
            print(f"✅ FIREBASE_PROJECT_ID = {project_id}")
        else:
            print("⚠️  FIREBASE_PROJECT_ID missing from .env")

        try:
            auth.get_user("test_user_id")
            print("✅ Firebase auth connection works")
        except Exception:
            print("ℹ️  Firebase auth module reachable (no test user found)")
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
else:
    print("⚠️  serviceAccountKey.json missing — Firebase may not initialize")

# === CHECK FASTAPI APP CONFIGURATION ===
print("\n⚙️ Checking FastAPI configuration...")
try:
    from app.main import app
    from fastapi import FastAPI

    if isinstance(app, FastAPI):
        print("✅ FastAPI instance found in app.main")
    else:
        print("⚠️  app.main.app is not a FastAPI instance")

    print(f"📛 App title: {app.title}")
    print(f"📜 App description: {app.description if app.description else '(none)'}")
    print(f"🧩 Registered routes: {len(app.routes)}")

    client = TestClient(app)
    print("\n🌐 FastAPI app test:")

    # === Measure API Response Time ===
    start_time = time.perf_counter()
    response = client.get("/")
    end_time = time.perf_counter()
    elapsed = end_time - start_time

    if response.status_code in [200, 404]:
        print(f"✅ App is responsive (status {response.status_code})")
    else:
        print(f"⚠️  Unexpected status code: {response.status_code}")

    print(f"⏱  Response time: {elapsed:.4f} seconds")

    if elapsed > 1.0:
        print("⚠️  Slow response detected — possible buffering or heavy I/O in startup route")
    elif elapsed > 0.3:
        print("ℹ️  Moderate response time, may indicate small processing delay")
    else:
        print("✅  Response speed is optimal")

    # === Optional: Test large response for buffering behavior ===
    try:
        print("\n🧪 Testing buffering (large payload simulation)...")
        buffer_start = time.perf_counter()
        res = client.get("/large-test")  # Optional: route to test payloads
        buffer_end = time.perf_counter()
        buffer_time = buffer_end - buffer_start

        print(f"⏱  Buffer test duration: {buffer_time:.4f} seconds")
        if buffer_time > 2.0:
            print("⚠️  Possible response buffering or serialization slowdown")
        else:
            print("✅  No significant buffering detected")
    except Exception:
        print("ℹ️  Skipped buffering test (no /large-test route found)")

except Exception as e:
    print(f"❌ FastAPI app failed: {e}")

# === CHECK APP MODULES ===
modules_to_check = [
    "app.main",
    "app.routes.auth",
    "app.routes.profiles",
    "app.database.firestore",
    "app.utils.firebase_utils",
    "app.models.user_models"
]

print("\n🧩 Importing internal modules...")
for module in modules_to_check:
    try:
        importlib.import_module(module)
        print(f"✅ {module} imported successfully")
    except Exception as e:
        print(f"❌ {module} failed: {e}")

# === CHECK PORT AVAILABILITY ===
def is_port_in_use(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

port = int(os.getenv("PORT", 8000))
if is_port_in_use(port):
    print(f"⚠️  Port {port} is already in use — choose another one")
else:
    print(f"✅ Port {port} is free")

# === TEST LOGIN ENDPOINT ===
print("\n🔐 Checking adaptive API performance test...")

# === Determine which base URL to use ===
default_local_url = "http://127.0.0.1:8000"
env_backend_url = os.getenv("BACKEND_URL", "").strip()

if env_backend_url:
    base_url = env_backend_url
    print(f"🌍 Using BACKEND_URL from .env → {base_url}")
else:
    # Check if local server responds
    try:
        ping = requests.get(f"{default_local_url}/", timeout=2)
        if ping.status_code in [200, 404]:
            base_url = default_local_url
            print(f"💻 Local server detected at {base_url}")
        else:
            raise Exception()
    except Exception:
        base_url = "https://your-vercel-backend.vercel.app"
        print(f"☁️  Falling back to default remote base URL → {base_url}")

# === Test /api/login endpoint ===
print(f"\n🚦 Testing POST {base_url}/auth/login ...")

login_data = {
    "email": "google@gmail.com",
    "password": "google@gmail.com"
}

try:
    start_time = time.perf_counter()
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=10)
    end_time = time.perf_counter()

    duration = end_time - start_time
    print(f"⏱  Total time: {duration:.4f} seconds")
    print(f"📡 Status code: {response.status_code}")
    print(f"📦 Response size: {len(response.text)} bytes")

    # Speed diagnostics
    if duration > 5:
        print("❌ Extremely slow — backend may be hanging or Firebase network latency high.")
    elif duration > 2:
        print("⚠️  Slow — possibly blocked on Firebase/DB auth.")
    elif duration > 1:
        print("ℹ️  Moderate — may include token verification delay.")
    else:
        print("✅  Fast response — API performing well.")

    # Optional: print a trimmed preview of the response
    print("\n🔍 Response preview:")
    print(response.text[:400])

except requests.exceptions.ConnectionError:
    print("❌ Could not connect to API — check if server is running.")
except requests.exceptions.Timeout:
    print("❌ Timeout — API took too long to respond.")
except Exception as e:
    print(f"❌ Unexpected error: {e}")


print("=============================================")
print("✅ DIAGNOSTICS COMPLETE")
print("=============================================")
