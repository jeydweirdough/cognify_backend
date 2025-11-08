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
from .config import TEST_PREFIX
from google.cloud.firestore_v1.base_query import FieldFilter


async def cleanup_test_data():
    """Remove all test data from Firestore by iterating documents and
    deleting those whose document ID starts with the configured TEST_PREFIX.
    """
    print("🔄 Starting test data cleanup...")

    # --- FIX: Added all collections that store test or generated data ---
    collections = [
        "user_profiles",
        "subjects",
        "modules",
        "activities",
        "assessments",
        "quizzes",
        "recommendations",
        "tos",
        "generated_summaries",
        "generated_quizzes",
        "generated_flashcards",
        "student_analytics_reports" # This collection is used in routes/utilities.py
    ]
    # --- END FIX ---

    total_deleted = 0

    for collection_name in collections:
        col_ref = db.collection(collection_name)
        
        # This query relies on an "id" field *inside* the document
        # which we fixed in the populate script.
        query = col_ref.where(filter=FieldFilter('id', '>=', TEST_PREFIX))\
                       .where(filter=FieldFilter('id', '<', TEST_PREFIX + u'\uf8ff'))
        
        # --- ADDITION: Handle collections that might not have an 'id' field ---
        # e.g., student_analytics_reports, which uses the doc ID
        # We'll just query by doc ID for those as a fallback.
        
        docs_to_delete = []
        
        try:
            docs = query.stream()
            count = 0
            for doc in docs:
                # The query should be precise, but we double-check the doc ID itself
                if doc.id.startswith(TEST_PREFIX):
                    docs_to_delete.append(doc.reference)
                    count += 1
        except Exception as e:
            # This query fails if the 'id' field doesn't exist (e.g., student_analytics_reports)
            # print(f"Warning: Could not query by 'id' field for {collection_name}. Error: {e}")
            # print(f"Trying to clean {collection_name} by Document ID prefix...")
            
            # Query by document ID (which is less efficient but necessary)
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

    print(f"\n🧹 Cleanup complete! Removed {total_deleted} test documents")


if __name__ == "__main__":
    if str(BASE_DIR) not in sys.path:
         sys.path.insert(0, str(BASE_DIR))
         
    from core.firebase import db
    from google.cloud.firestore_v1.base_query import FieldFilter
    
    asyncio.run(cleanup_test_data())