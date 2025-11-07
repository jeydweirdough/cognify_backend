import os, json, firebase_admin
from firebase_admin import credentials, firestore
# --- 1. Import the settings ---
from core.config import settings

if not firebase_admin._apps:
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))
        print("Firebase initialized with environment service account.")
    else:
        cred = credentials.Certificate("serviceAccountKey.json")
        print("Firebase initialized with local service account.")

    # --- 2. Add the storageBucket option ---
    firebase_admin.initialize_app(cred, {
        'storageBucket': settings.FIREBASE_STORAGE_BUCKET
    })

db = firestore.client()