"""Command-line interface for test data management."""
import argparse
import asyncio
from .populate_test_data import populate_test_data
from .cleanup_test_data import cleanup_test_data

def main():
    """Entry point for test data CLI."""
    parser = argparse.ArgumentParser(description="Cognify test data management")
    parser.add_argument(
        "action",
        choices=["populate", "cleanup"],
        help="Action to perform: populate (create test data) or cleanup (remove test data)"
    )

    args = parser.parse_args()

    if args.action == "populate":
        print("\n📝 Starting test data population...\n")
        asyncio.run(populate_test_data())
    else:  # cleanup
        print("\n🧹 Starting test data cleanup...\n")
        asyncio.run(cleanup_test_data())

if __name__ == "__main__":
    main()