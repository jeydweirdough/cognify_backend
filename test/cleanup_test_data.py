import asyncio
import sys
from pathlib import Path

# Add project root to path to import core modules
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from core.firebase import db
from test.config import TEST_PREFIX

# List of collections to check and clean
# Added 'student_analytics_reports' and 'subjects' as requested
COLLECTIONS_TO_CLEAN = [
    "student_analytics_reports", 
    "subjects",
    "assessments",
    "diagnostic_assessments",
    "diagnostic_results",
    "recommendations",
    "activities",
    "study_sessions",
    "modules",
    "quizzes",
    "tos",
    "user_profiles"
]

async def cleanup_test_data():
    print(f"\n🧹 STARTING CLEANUP (Target Prefix: '{TEST_PREFIX}')...")
    print("="*60)

    total_deleted = 0

    for collection_name in COLLECTIONS_TO_CLEAN:
        print(f"   > Scanning collection: '{collection_name}'...")
        
        # Fetch all documents
        # Note: Firestore queries by ID prefix aren't directly supported efficiently, 
        # so we fetch and filter. For test data environments, this is acceptable.
        docs = list(db.collection(collection_name).stream())
        
        batch = db.batch()
        count = 0
        deleted_in_col = 0
        
        for doc in docs:
            # SAFETY CHECK: Only delete documents starting with the test prefix (e.g., 'demo_')
            if doc.id.startswith(TEST_PREFIX):
                batch.delete(doc.reference)
                count += 1
                deleted_in_col += 1
                total_deleted += 1
                
                # Commit in batches of 400 (Firestore limit is 500)
                if count >= 400:
                    batch.commit()
                    batch = db.batch()
                    count = 0
        
        # Commit remaining documents in the batch
        if count > 0:
            batch.commit()
            
        if deleted_in_col > 0:
            print(f"     ✅ Deleted {deleted_in_col} test documents.")
        else:
            print("     - No matching test data found.")

    print("="*60)
    print(f"✨ CLEANUP COMPLETE! Total documents removed: {total_deleted}\n")

if __name__ == "__main__":
    asyncio.run(cleanup_test_data())