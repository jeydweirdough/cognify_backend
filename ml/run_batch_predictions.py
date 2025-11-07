# ml/run_batch_predictions.py
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
# --- REMOVED: 'requests' and 'time' imports ---

# --- 1. Setup Firebase Admin ---
print("Starting daily prediction batch job...")
try:
    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        cred_dict = json.loads(sa_json)
        cred = credentials.Certificate(cred_dict)
        print("Firebase initialized from GitHub Secret.")
    else:
        cred = credentials.Certificate("serviceAccountKey.json")
        print("Firebase initialized from local serviceAccountKey.json.")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    print("Firebase connection successful.")
except Exception as e:
    print(f"CRITICAL: Failed to initialize Firebase: {e}")
    sys.exit(1)

# --- Define collection names ---
ANALYTICS_COLLECTION = "student_analytics_reports"
PREDICTIONS_COLLECTION = "daily_predictions"

# --- 2. Helper Functions (from your old services) ---

async def get_role_id_by_designation(designation: str) -> str | None:
    roles_query = db.collection("roles").where(
        filter=FieldFilter("designation", "==", designation)
    ).limit(1).stream()
    for doc in roles_query:
        return doc.id
    return None

async def get_student_analytics(student_id: str) -> dict:
    activities_ref = db.collection("activities").where(
        filter=FieldFilter("user_id", "==", student_id)
    ).where(
        filter=FieldFilter("deleted", "!=", True) 
    )
    activities = [doc.to_dict() for doc in activities_ref.get()]

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

# --- REMOVED: get_ai_motivational_quote function ---

async def generate_all_student_features():
    print("Generating features for all students...")
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        print("Error: 'student' role not found.")
        return pd.DataFrame(), []

    student_profiles_query = db.collection("user_profiles").where(
        filter=FieldFilter("role_id", "==", student_role_id)
    ).where(
        filter=FieldFilter("deleted", "!=", True)
    )
    student_profiles = [doc.to_dict() for doc in student_profiles_query.stream()]

    all_features = []
    all_analytics_reports = []
    
    for profile in student_profiles:
        student_id = profile.get("id")
        if not student_id:
            print(f"Warning: Skipping profile with no 'id' field. Email: {profile.get('email')}")
            continue

        analytics = await get_student_analytics(student_id)
        features = {
            "student_id": student_id,
            "pre_assessment_score": profile.get("pre_assessment_score", 0) or 0,
            "overall_score": analytics["summary"]["overall_score"],
            "total_activities": analytics["summary"]["total_activities"],
            "time_spent_sec": analytics["summary"]["time_spent_sec"]
        }
        
        bloom_features = {}
        for item in analytics["performance_by_bloom"]:
            features[f"bloom_{item['bloom_level']}"] = item['score']
            bloom_features[item['bloom_level']] = round(item['score'], 2)

        all_features.append(features)
        
        report_data = {
            "student_id": student_id,
            "summary": analytics["summary"],
            "performance_by_bloom": bloom_features,
        }
        all_analytics_reports.append(report_data)

    if not all_features:
        return pd.DataFrame(), []

    df = pd.DataFrame(all_features).fillna(0)
    return df, all_analytics_reports

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
            return joblib.load("ml/pass_predictor.joblib")
        except FileNotFoundError:
            print("ERROR: ml/pass_predictor.joblib not found. Training failed.")
            return None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    def _fit_model(X, y):
        model = LogisticRegression(max_iter=1000)
        model.fit(X, y)
        return model
    
    loop = asyncio.get_event_loop()
    model = await loop.run_in_executor(None, _fit_model, X_train, y_train)
    
    try:
        acc = accuracy_score(y_test, model.predict(X_test))
        print(f"New model trained. Accuracy: {acc * 100:.2f}%")
    except Exception as e:
        print(f"Could not calculate accuracy (not enough test data): {e}")

    joblib.dump(model, "ml/pass_predictor.joblib")
    return model

# --- 3. Main Script Logic ---
async def main():
    features_df, student_reports = await generate_all_student_features()
    
    if features_df.empty:
        print("No features generated. Exiting.")
        return

    model = await train_model(features_df)
    if model is None:
        print("Model training/loading failed. Exiting.")
        return

    print("Running predictions on all students...")
    X_live = features_df.drop(columns=['student_id', 'overall_score', 'passed'], errors='ignore')
    model_columns = model.feature_names_in_
    X_live = X_live.reindex(columns=model_columns, fill_value=0)

    predictions = model.predict(X_live)
    probabilities = model.predict_proba(X_live)[:, 1] 
    global_predictions_list = []
    
    print(f"Saving {len(student_reports)} individual analytics reports...")
    batch = db.batch()
    
    for i, report in enumerate(student_reports):
        student_id = report["student_id"]
        
        prediction_data = {
            "predicted_to_pass": bool(predictions[i]),
            "pass_probability": round(probabilities[i] * 100, 2)
        }
        
        report["prediction"] = prediction_data
        report["last_updated"] = firestore.SERVER_TIMESTAMP
        
        doc_ref = db.collection(ANALYTICS_COLLECTION).document(student_id)
        batch.set(doc_ref, report, merge=True) # merge=True ensures we don't overwrite existing motivation
        
        global_predictions_list.append({
            "student_id": student_id,
            **prediction_data
        })

    batch.commit()
    print(f"Successfully saved {len(student_reports)} combined reports to '{ANALYTICS_COLLECTION}'.")
    
    total_pass = sum(predictions)
    total_students = len(global_predictions_list)
    final_output = {
        "summary": {
            "total_students_predicted": total_students,
            "count_predicted_to_pass": int(total_pass),
            "count_predicted_to_fail": int(total_students - total_pass),
            "predicted_pass_rate": round((total_pass / total_students) * 100, 2) if total_students > 0 else 0
        },
        "predictions": global_predictions_list,
        "last_updated": firestore.SERVER_TIMESTAMP
    }

    print(f"Saving global prediction summary to '{PREDICTIONS_COLLECTION}'...")
    doc_ref = db.collection(PREDICTIONS_COLLECTION).document("latest")
    doc_ref.set(final_output)
    print("Batch job complete. Predictions and Analytics saved to Firestore.")

if __name__ == "__main__":
    asyncio.run(main())