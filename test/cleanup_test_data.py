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
# --- FIX: Import FieldFilter for the query ---
from google.cloud.firestore_v1.base_query import FieldFilter


async def cleanup_test_data():
    """Remove all test data from Firestore by iterating documents and
    deleting those whose document ID starts with the configured TEST_PREFIX.
    """
    print("🔄 Starting test data cleanup...")

    # Collections to clean (using your app's actual collection names)
    # --- FIX: Removed "roles" ---
    collections = [
        "user_profiles",
        "subjects",
        "modules",
        "activities",
        "assessments",
        "quizzes",
        "recommendations",
        "tos",
    ]

    total_deleted = 0

    for collection_name in collections:
        col_ref = db.collection(collection_name)
        
        # Firestore's "startswith" query requires a range
        # We query the 'id' field *within* the document
        query = col_ref.where(filter=FieldFilter('id', '>=', TEST_PREFIX))\
                       .where(filter=FieldFilter('id', '<', TEST_PREFIX + u'\uf8ff'))
        
        docs = query.stream()
        
        count = 0
        docs_to_delete = [] 
        for doc in docs:
            # The query should be precise, but we double-check the doc ID itself
            if doc.id.startswith(TEST_PREFIX):
                docs_to_delete.append(doc.reference)
                count += 1
        
        for doc_ref in docs_to_delete:
            doc_ref.delete()

        total_deleted += count
        if count > 0:
            print(f"✅ Deleted {count} test document(s) from '{collection_name}'")
        else:
            print(f"ℹ️  No test data found in '{collection_name}'")

    print(f"\n🧹 Cleanup complete! Removed {total_deleted} test documents")


if __name__ == "__main__":
    if str(BASE_DIR) not in sys.path:
         sys.path.insert(0, str(BASE_DIR))
         
    from core.firebase import db
    from google.cloud.firestore_v1.base_query import FieldFilter
    
    asyncio.run(cleanup_test_data())