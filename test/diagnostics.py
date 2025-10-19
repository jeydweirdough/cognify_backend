import importlib
import os
import sys
import socket
from pathlib import Path
from dotenv import load_dotenv
from fastapi.testclient import TestClient

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
    "python-dotenv": "dotenv",  # <-- Fix here: use actual import name
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
if firebase_key.exists():
    print(f"✅ Firebase key found: {firebase_key}")
else:
    print("⚠️  serviceAccountKey.json missing — Firebase may not initialize")

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

# === TEST FASTAPI APP ===
try:
    from app.main import app
    client = TestClient(app)
    response = client.get("/")
    print("\n🌐 FastAPI app test:")
    if response.status_code in [200, 404]:
        print("✅ App is responsive (root endpoint works or returns 404)")
    else:
        print(f"⚠️  App returned unexpected status code: {response.status_code}")
except Exception as e:
    print(f"❌ FastAPI app failed to start: {e}")

print("=============================================")
print("✅ DIAGNOSTICS COMPLETE")
print("=============================================")
