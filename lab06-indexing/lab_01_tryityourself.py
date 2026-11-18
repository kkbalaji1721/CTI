"""Lab 6.1 - Try It Yourself
Use $indexStats to measure actual index usage
after running queries multiple times.
"""

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))

for path in (project_root, os.path.dirname(project_root)):
    if path and path not in sys.path:
        sys.path.insert(0, path)

from config.connection import get_db, banner


def main():

    banner("Lab 6.1: Try It Yourself - Index Usage")

    # Connect to the existing database and collection
    db = get_db("nosql_labs")
    col = db["server_logs"]

    print(f"[OK] Connected to collection: {col.name}")
    print(f"[OK] Documents in collection: {col.count_documents({})}\n")

    # ---------------------------------------------------------
    # RUN QUERIES MULTIPLE TIMES
    # ---------------------------------------------------------

    print("=== Running Queries Multiple Times ===")

    # Query 1
    print("Running Query 1 - ERROR logs from payment-svc")

    for i in range(10):
        list(
            col.find({
                "level": "ERROR",
                "service": "payment-svc"
            })
        )

    # Query 2
    print("Running Query 2 - All 404 responses")

    for i in range(20):
        list(
            col.find({
                "status_code": 404
            })
        )

    # Query 3
    print("Running Query 3 - Slow API gateway requests")

    for i in range(15):
        list(
            col.find({
                "service": "api-gateway",
                "response_time_ms": {
                    "$gt": 3000
                }
            })
        )

    print("\n[OK] All queries executed multiple times.\n")

    # ---------------------------------------------------------
    # USE $indexStats
    # ---------------------------------------------------------

    print("=== $indexStats: Actual Index Usage ===")

    stats = list(
        col.aggregate([
            {
                "$indexStats": {}
            }
        ])
    )

    for stat in stats:

        index_name = stat.get(
            "name",
            "Unknown"
        )

        operations = stat.get(
            "accesses",
            {}
        ).get(
            "ops",
            0
        )

        since = stat.get(
            "accesses",
            {}
        ).get(
            "since",
            "N/A"
        )

        print(f"Index: {index_name}")
        print(f"  Operations: {operations}")
        print(f"  Since: {since}")
        print()

    # ---------------------------------------------------------
    # IDENTIFY MOST FREQUENTLY USED INDEX
    # ---------------------------------------------------------

    print("=== Most Frequently Used Index ===")

    # Ignore the default _id index
    user_indexes = [
        stat
        for stat in stats
        if stat.get("name") != "_id_"
    ]

    if user_indexes:

        most_used = max(
            user_indexes,
            key=lambda stat: stat.get(
                "accesses",
                {}
            ).get(
                "ops",
                0
            )
        )

        most_used_name = most_used.get(
            "name",
            "Unknown"
        )

        most_used_operations = most_used.get(
            "accesses",
            {}
        ).get(
            "ops",
            0
        )

        print(
            f"Most frequently used index: "
            f"{most_used_name}"
        )

        print(
            f"Number of operations: "
            f"{most_used_operations}"
        )

    else:

        print("No user-created indexes were used.")

    # ---------------------------------------------------------
    # INDEX SUMMARY
    # ---------------------------------------------------------

    print("\n=== Index Summary ===")

    for index in col.list_indexes():

        print(
            f"  {index['name']:30} "
            f"keys={index['key']}"
        )

    banner("Try It Yourself Complete")


if __name__ == "__main__":
    main()