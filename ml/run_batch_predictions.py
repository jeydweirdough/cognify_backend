# run_batch_predictions.py
import os
import sys
import asyncio
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
import json
from google.cloud.firestore_v1.base_query import FieldFilter

# --- 1. Setup Firebase Admin ---
print("Starting daily prediction batch job...")
try:
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        cred_dict = json.loads(sa_json)
        cred = credentials.Certificate(cred_dict)
        print("Firebase initialized from GitHub Secret.")
    else:
        # Fallback for local testing (if you run `python run_batch_predictions.py`)
        cred = credentials.Certificate("serviceAccountKey.json")
        print("Firebase initialized from local serviceAccountKey.json.")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    print("Firebase connection successful.")
except Exception as e:
    print(f"CRITICAL: Failed to initialize Firebase: {e}")
    sys.exit(1)

# --- 2. Helper Functions (from your old services) ---

async def get_role_id_by_designation(designation: str) -> str | None:
    roles_query = db.collection("roles").where(
        filter=FieldFilter("designation", "==", designation)
    ).limit(1).stream()
    for doc in roles_query:
        return doc.id
    return None

async def get_student_analytics(student_id: str) -> dict:
    activities_ref = db.collection("activities").where("user_id", "==", student_id)
    activities = [doc.to_dict() for doc in await activities_ref.get()]

    if not activities:
        return {"summary": {"overall_score": 0, "total_activities": 0, "time_spent_sec": 0}, "performance_by_bloom": []}

    df = pd.DataFrame(activities)
    df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0.0)

    bloom_performance = df.groupby('bloom_level')['score'].mean().reset_index()
    bloom_dict = bloom_performance.to_dict('records')

    summary = {
        "total_activities": len(df),
        "overall_score": round(df['score'].mean(), 2),
        "time_spent_sec": int(df['duration'].sum() if 'duration' in df.columns else 0)
    }
    return {"summary": summary, "performance_by_bloom": bloom_dict}

async def generate_all_student_features() -> pd.DataFrame:
    print("Generating features for all students...")
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        print("Error: 'student' role not found.")
        return pd.DataFrame()

    student_profiles = [doc.to_dict() for doc in db.collection("user_profiles").where(filter=FieldFilter("role_id", "==", student_role_id)).where(filter=FieldFilter("deleted", "!=", True)).stream()]

    all_features = []
    for profile in student_profiles:
        student_id = profile.get("id")
        if not student_id:
            continue

        analytics = await get_student_analytics(student_id)

        features = {
            "student_id": student_id,
            "pre_assessment_score": profile.get("pre_assessment_score", 0) or 0,
            "overall_score": analytics["summary"]["overall_score"],
            "total_activities": analytics["summary"]["total_activities"],
            "time_spent_sec": analytics["summary"]["time_spent_sec"]
        }
        for item in analytics["performance_by_bloom"]:
            features[f"bloom_{item['bloom_level']}"] = item['score']

        all_features.append(features)

    if not all_features:
        return pd.DataFrame()

    df = pd.DataFrame(all_features).fillna(0)
    return df

async def train_model(features_df: pd.DataFrame):
    print("Starting model training...")
    PASSING_THRESHOLD = 75.0 

    if features_df.empty:
        print("No student data found for training.")
        return None

    features_df['passed'] = (features_df['overall_score'] >= PASSING_THRESHOLD).astype(int)

    X = features_df.drop(columns=['student_id', 'passed', 'overall_score'], errors='ignore')
    y = features_df['passed']

    if len(X) < 2 or len(np.unique(y)) < 2:
        print("Not enough data or classes to train. Using fallback model.")
        try:
            # Load the fallback model from your repo
            return joblib.load("ml/pass_predictor.joblib")
        except FileNotFoundError:
            print("ERROR: ml/pass_predictor.joblib not found. Training failed.")
            return None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"New model trained. Accuracy: {acc * 100:.2f}%")

    # Save the new model to disk (this only saves to the temporary server, but it's good practice)
    joblib.dump(model, "ml/pass_predictor.joblib")
    return model

# --- 3. Main Script Logic ---
async def main():
    features_df = await generate_all_student_features()
    if features_df.empty:
        print("No features generated. Exiting.")
        return

    model = await train_model(features_df)
    if model is None:
        print("Model training/loading failed. Exiting.")
        return

    print("Running predictions on all students...")
    student_ids = features_df['student_id']
    X_live = features_df.drop(columns=['student_id', 'overall_score', 'passed'], errors='ignore')

    model_columns = model.feature_names_in_
    X_live = X_live.reindex(columns=model_columns, fill_value=0)

    predictions = model.predict(X_live)
    probabilities = model.predict_proba(X_live)[:, 1] 

    results_by_student = []
    for i, student_id in enumerate(student_ids):
        results_by_student.append({
            "student_id": student_id,
            "predicted_to_pass": bool(predictions[i]),
            "pass_probability": round(probabilities[i] * 100, 2)
        })

    total_pass = sum(predictions)
    total_students = len(results_by_student)

    final_output = {
        "summary": {
            "total_students_predicted": total_students,
            "count_predicted_to_pass": int(total_pass),
            "count_predicted_to_fail": int(total_students - total_pass),
            "predicted_pass_rate": round((total_pass / total_students) * 100, 2) if total_students > 0 else 0
        },
        "predictions": results_by_student,
        "last_updated": firestore.SERVER_TIMESTAMP
    }

    print(f"Saving {len(results_by_student)} predictions to Firestore...")
    doc_ref = db.collection("daily_predictions").document("latest")
    doc_ref.set(final_output)
    print("Batch job complete. Predictions saved to Firestore.")

if __name__ == "__main__":
    asyncio.run(main())