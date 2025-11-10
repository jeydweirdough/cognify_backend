"""Clean up test data from Firestore."""
import asyncio
import sys
import os
from pathlib import Path

# --- Add base directory to path ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
# ----------------------------------

from core.firebase import db
# --- NEW: Import Firebase Auth ---
from firebase_admin import auth
# Import from config to ensure it's the single source of truth
from .config import TEST_PREFIX
from google.cloud.firestore_v1.base_query import FieldFilter


async def cleanup_test_data():
    """Remove all test data from Firestore by iterating documents and
    deleting those whose document ID starts with the configured TEST_PREFIX.
    
    UPDATED: Now also deletes the corresponding users from Firebase Auth.
    """
    print(f"🔄 Starting test data cleanup...")
    print(f"Using TEST_PREFIX: {TEST_PREFIX}")

    # --- UPDATED LIST ---
    # Renamed 'enhanced_recommendations' to 'recommendations'
    collections = [
        "user_profiles",
        "subjects",
        "modules",
        "activities",
        "assessments", 
        "quizzes", 
        "recommendations", # This is now the main recommendations collection
        "tos",
        "generated_summaries",
        "generated_quizzes",
        "generated_flashcards",
        "student_motivations",
        "diagnostic_assessments",
        "diagnostic_results",
        "study_sessions", 
        "content_verifications", 
        "student_analytics_reports"
    ]
    # --- END UPDATED LIST ---

    total_deleted = 0

    print("🧹 Cleaning up Firestore Database collections...")
    for collection_name in collections:
        col_ref = db.collection(collection_name)
        
        query = col_ref.where(filter=FieldFilter('id', '>=', TEST_PREFIX))\
                       .where(filter=FieldFilter('id', '<', TEST_PREFIX + u'\uf8ff'))
        
        docs_to_delete = []
        
        try:
            docs = query.stream()
            count = 0
            for doc in docs:
                if doc.id.startswith(TEST_PREFIX):
                    docs_to_delete.append(doc.reference)
                    count += 1
        except Exception as e:
            # Fallback for collections without an 'id' field
            all_docs = col_ref.stream()
            count = 0
            for doc in all_docs:
                 if doc.id.startswith(TEST_PREFIX):
                    docs_to_delete.append(doc.reference)
                    count += 1

        
        for doc_ref in docs_to_delete:
            doc_ref.delete()

        total_deleted += len(docs_to_delete)
        if len(docs_to_delete) > 0:
            print(f"✅ Deleted {len(docs_to_delete)} test document(s) from '{collection_name}'")
        else:
            print(f"ℹ️  No test data found in '{collection_name}'")

    print(f"\nFirestore cleanup complete! Removed {total_deleted} test documents.")
    
    # ============================================================
    # --- NEW: CLEANUP FIREBASE AUTHENTICATION ---
    # ============================================================
    print("\n🔥 Cleaning up Firebase Authentication users...")
    
    uids_to_delete = []
    total_auth_deleted = 0
    
    try:
        # Iterate over all users in batches
        for user in auth.list_users().iterate_all():
            if user.uid.startswith(TEST_PREFIX):
                uids_to_delete.append(user.uid)
        
        if not uids_to_delete:
            print("ℹ️  No test users found in Authentication.")
        else:
            print(f"Found {len(uids_to_delete)} test auth users. Deleting...")
            # Note: Deleting users one by one is more robust than batch delete
            # which has a limit of 1000 and requires more complex error handling.
            for uid in uids_to_delete:
                try:
                    auth.delete_user(uid)
                    total_auth_deleted += 1
                except Exception as e:
                    print(f"Warning: Could not delete auth user {uid}. Error: {e}")
            
            print(f"✅ Deleted {total_auth_deleted} test users from Authentication.")

    except Exception as e:
        print(f"❌ Error listing auth users: {e}")
    # --- END NEW SECTION ---

    print("\n" + "=" * 60)
    print(f"🧹 FULL CLEANUP COMPLETE!")
    print(f"  - Removed {total_deleted} Firestore documents.")
    print(f"  - Removed {total_auth_deleted} Firebase Auth users.")
    print("=" * 60)


if __name__ == "__main__":
    if str(BASE_DIR) not in sys.path:
         sys.path.insert(0, str(BASE_DIR))
         
    from core.firebase import db
    # --- NEW: Import Auth ---
    from firebase_admin import auth
    from google.cloud.firestore_v1.base_query import FieldFilter
    
    asyncio.run(cleanup_test_data())