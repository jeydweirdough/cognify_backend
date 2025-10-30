import pandas as pd
import joblib
import asyncio
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import sys
import os
import numpy as np

# --- Add this block to import app modules ---
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
# ---------------------------------------------

from services.analytics_service import generate_all_student_features
# (We no longer need core.firebase or core.config)

# --- Your Project's Definition of "Pass" ---
PASSING_THRESHOLD = 75.0 

async def train():
    """
    Fetches all student data, generates features, trains a pass/fail
    classifier, and RETURNS IT TO BE HELD IN MEMORY.
    """
    print("Starting model training...")
    
    # 1. Generate features for all students
    print("Generating features for all students...")
    features_df = await generate_all_student_features()
    
    if features_df.empty:
        print("No student data found. Exiting training.")
        return None # Return None if no data

    # 2. Create the "Y" variable (the "answer")
    features_df['passed'] = (features_df['overall_score'] >= PASSING_THRESHOLD).astype(int)
    
    # 3. Prepare data for the model
    X = features_df.drop(columns=['student_id', 'passed', 'overall_score'], errors='ignore')
    y = features_df['passed']

    # 4. Check for enough data
    if len(X) < 2:
        print(f"Not enough data to train (only {len(X)} samples). Need at least 2. Exiting.")
        return None

    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        print("\n--- TRAINING FAILED: NOT ENOUGH DATA CLASSES ---")
        print(f"The model needs samples of at least 2 classes (e.g., 'pass' and 'fail') to learn.")
        print(f"Your {len(X)} student samples only contain one class: {unique_classes[0]} (0=Fail, 1=Pass).")
        print(f"Exiting training.\n")
        return None
        
    print(f"Training model on {len(X)} student samples...")

    # 5. Split data for training and testing
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 6. Train the "light" AI model
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    # 7. Check how good the model is
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy on Test Set: {acc * 100:.2f}%")

    # --- 8. NO SAVING ---
    # We are not saving the file to disk or storage.
    # We just return the trained model object.
    print("Model training complete. Returning model to memory.")
    
    # 9. Return the newly trained model
    return model

if __name__ == "__main__":
    # This check is needed so the script can find 'services', 'core', etc.
    if str(Path(__file__).resolve().parents[1]) not in sys.path:
        sys.path.append(str(Path(__file__).resolve().parents[1]))
        
    from services.analytics_service import generate_all_student_features
    # (No firebase imports needed here)

    asyncio.run(train())

