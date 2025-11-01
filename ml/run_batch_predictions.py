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
# --- NEW: Import requests library ---
# Note: You MUST add 'requests' to your 'requirements-ml.txt' file
import requests 
import time

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
    # --- THIS IS NOW EFFICIENT ---
    # We create the query and add the 'deleted' filter
    activities_ref = db.collection("activities").where(
        filter=FieldFilter("user_id", "==", student_id)
    ).where(
        filter=FieldFilter("deleted", "!=", True) # This makes it efficient
    )
    
    # We run .get() which requires an index, but is the correct way
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

# --- NEW: Function to call Gemini API (using 'requests') ---
def get_ai_motivational_quote(report_data: dict, retry_count=3) -> str:
    """
    Calls the Gemini API to generate a personalized motivational quote.
    This is a SYNCHRONOUS function using 'requests'.
    """
    try:
        # 1. Extract data for the prompt
        prob = report_data.get("prediction", {}).get("pass_probability", 75.0)
        activities = report_data.get("summary", {}).get("total_activities", 10)
        bloom = report_data.get("performance_by_bloom", {})
        
        # Find the weakest area
        weakest_area = ""
        if bloom:
            # Find the bloom level with the minimum score
            weakest_area = min(bloom.items(), key=lambda item: item[1])[0]

        # 2. Create the prompt
        system_prompt = (
            "You are an encouraging and wise mentor for a psychology student "
            "preparing for their licensure exam. Your role is to provide a single, "
            "short (1-2 sentence) motivational quote. Be specific, positive, and forward-looking. "
            "Do not use markdown."
        )
        
        user_query = (
            f"My student's profile: "
            f"Pass Probability: {prob}%. "
            f"Total Activities: {activities}. "
            f"Weakest Area: '{weakest_area}'. "
            "Write a single, new motivational quote for them."
        )

        # 3. Call the Gemini API
        api_key = "" # This is handled by the platform
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"
        
        payload = {
            "contents": [{ "parts": [{ "text": user_query }] }],
            "systemInstruction": { "parts": [{ "text": system_prompt }] },
        }

        # 4. Make the request using 'requests' (synchronous)
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status() # Raise an error for bad responses
        
        result = response.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        if text:
            print(f"Generated AI quote for {report_data['student_id']}.")
            return text.strip().strip('"')

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429 and retry_count > 0: # Handle rate limiting
            print(f"Rate limited. Retrying in {6 - retry_count}s...")
            time.sleep(6 - retry_count) # Exponential backoff
            return get_ai_motivational_quote(report_data, retry_count - 1)
        print(f"Error generating AI quote (HTTPError): {e}")
    except Exception as e:
        print(f"Error generating AI quote: {e}")

    # --- Fallback Logic (if API fails) ---
    print(f"Using fallback quote for student {report_data['student_id']}.")
    if activities <= 5:
        return "The journey of a thousand miles begins with a single step. Let's get started with one module today."
    elif prob < 60:
        return f"It looks like '{weakest_area}' is a challenge. Failure is not fatal: it's the courage to continue that counts. Let's review that area."
    elif prob > 95:
        return "Great work! You're acing this. Keep that passion and mastery."
    else:
        return "You're on the right track! Success is the sum of small efforts, repeated day in and day out. Keep going."


async def generate_all_student_features():
    print("Generating features for all students...")
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        print("Error: 'student' role not found.")
        return pd.DataFrame(), [] # Return empty list for reports

    # --- THIS IS THE EFFICIENT QUERY ---
    # This is the query that failed before. It is the *correct* query.
    # It will require an index, which you must create.
    student_profiles_query = db.collection("user_profiles").where(
        filter=FieldFilter("role_id", "==", student_role_id)
    ).where(
        filter=FieldFilter("deleted", "!=", True)
    )
    
    student_profiles = [doc.to_dict() for doc in student_profiles_query.stream()]

    all_features = []
    # --- NEW: We will also store the full analytics report ---
    all_analytics_reports = []
    
    for profile in student_profiles:
        student_id = profile.get("id")
        if not student_id:
            continue

        # Run the async analytics function in the event loop
        analytics = await get_student_analytics(student_id)

        # This `features` dict is what the ML model needs
        features = {
            "student_id": student_id,
            "pre_assessment_score": profile.get("pre_assessment_score", 0) or 0,
            "overall_score": analytics["summary"]["overall_score"],
            "total_activities": analytics["summary"]["total_activities"],
            "time_spent_sec": analytics["summary"]["time_spent_sec"]
        }
        
        bloom_features = {}
        for item in analytics["performance_by_bloom"]:
            # Add to ML features
            features[f"bloom_{item['bloom_level']}"] = item['score']
            # Add to bloom_features for the report
            bloom_features[item['bloom_level']] = round(item['score'], 2)

        all_features.append(features)
        
        # --- NEW: Create the full analytics report for this student ---
        # This is the data that matches your manuscript's goals
        report_data = {
            "student_id": student_id,
            "summary": analytics["summary"],
            "performance_by_bloom": bloom_features, # Use the clean dict
            # We will add "prediction" and "ai_motivation" data later
        }
        all_analytics_reports.append(report_data)

    if not all_features:
        return pd.DataFrame(), []

    df = pd.DataFrame(all_features).fillna(0)
    
    # --- NEW: Return both the features DataFrame and the list of reports ---
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
            # Load the fallback model from your repo
            return joblib.load("ml/pass_predictor.joblib")
        except FileNotFoundError:
            print("ERROR: ml/pass_predictor.joblib not found. Training failed.")
            return None

    # --- THIS IS THE FIX ---
    # 1. Define the training and test sets *before* trying to use them.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 2. Define a simple, synchronous function for the blocking ML work
    def _fit_model(X, y):
        model = LogisticRegression(max_iter=1000)
        model.fit(X, y)
        return model
    
    # 3. Get the event loop and run the blocking function in a thread
    loop = asyncio.get_event_loop()
    # We pass _fit_model, X_train, and y_train as arguments
    model = await loop.run_in_executor(None, _fit_model, X_train, y_train)
    
    # --- END FIX ---

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"New model trained. Accuracy: {acc * 100:.2f}%")

    # Save the new model to disk (this only saves to the temporary server, but it's good practice)
    joblib.dump(model, "ml/pass_predictor.joblib")
    return model

# --- 3. Main Script Logic ---
async def main():
    # --- NEW: Get both features and reports ---
    features_df, student_reports = await generate_all_student_features()
    
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

    # --- NEW: Combine analytics and predictions ---
    global_predictions_list = []
    
    print(f"Saving {len(student_reports)} individual analytics reports...")
    batch = db.batch()
    loop = asyncio.get_event_loop()
    
    for i, report in enumerate(student_reports):
        student_id = report["student_id"]
        
        # Create the prediction data
        prediction_data = {
            "predicted_to_pass": bool(predictions[i]),
            "pass_probability": round(probabilities[i] * 100, 2)
        }
        
        # Add the prediction data to the main report
        report["prediction"] = prediction_data
        
        # --- NEW: Generate and add the AI motivational quote ---
        # We run the blocking 'requests' call in a thread
        ai_quote = await loop.run_in_executor(None, get_ai_motivational_quote, report)
        
        report["ai_motivation"] = ai_quote
        report["last_updated"] = firestore.SERVER_TIMESTAMP
        
        # Add this combined report to the batch
        doc_ref = db.collection(ANALYTICS_COLLECTION).document(student_id)
        batch.set(doc_ref, report)
        
        # Also add the prediction to the global list
        global_predictions_list.append({
            "student_id": student_id,
            **prediction_data
        })

    # Commit the batch to save all student reports
    batch.commit()
    print(f"Successfully saved {len(student_reports)} combined reports to '{ANALYTICS_COLLECTION}'.")
    
    # --- Now save the GLOBAL summary for the admin dashboard ---
    total_pass = sum(predictions)
    total_students = len(global_predictions_list)

    final_output = {
        "summary": {
            "total_students_predicted": total_students,
            "count_predicted_to_pass": int(total_pass),
            "count_predicted_to_fail": int(total_students - total_pass),
            "predicted_pass_rate": round((total_pass / total_students) * 100, 2) if total_students > 0 else 0
        },
        "predictions": global_predictions_list, # This is the list of individual predictions
        "last_updated": firestore.SERVER_TIMESTAMP
    }

    print(f"Saving global prediction summary to '{PREDICTIONS_COLLECTION}'...")
    doc_ref = db.collection(PREDICTIONS_COLLECTION).document("latest")
    doc_ref.set(final_output)
    print("Batch job complete. Predictions and Analytics saved to Firestore.")

if __name__ == "__main__":
    # Add 'requests' to the ml requirements
    # You must run: pip install -r requirements-ml.txt
    # after adding 'requests' to that file.
    asyncio.run(main())

