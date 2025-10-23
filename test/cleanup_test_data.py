"""Clean up test data from Firestore."""
import asyncio
from database.firestore import db
from .config import TEST_PREFIX


async def cleanup_test_data():
    """Remove all test data from Firestore by iterating documents and
    deleting those whose document ID starts with the configured TEST_PREFIX.

    This avoids using `__name__`/`__key__` range filters which require
    Key objects and can produce InvalidArgument errors.
    """
    print("🔄 Starting test data cleanup...")

    # Collections to clean
    collections = [
        "students",
        "modules",
        "activities",
        "assessments",
        "quizzes",
        "recommendations",
        "tos",
    ]

    total_deleted = 0

    for collection in collections:
        col_ref = db.collection(collection)

        # Stream all documents in the collection, check id prefix, delete matches
        docs = col_ref.stream()

        count = 0
        for doc in docs:
            # doc.id is the document ID (without the collection path)
            if doc.id.startswith(TEST_PREFIX):
                # delete synchronously (Firestore client will handle network IO)
                doc.reference.delete()
                count += 1

        total_deleted += count
        print(f"✅ Deleted {count} test document(s) from {collection}")

    print(f"\n🧹 Cleanup complete! Removed {total_deleted} test documents")


if __name__ == "__main__":
    asyncio.run(cleanup_test_data())