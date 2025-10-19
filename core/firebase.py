import os, json, firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    cred = credentials.Certificate(json.loads(sa_json)) if sa_json else credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
