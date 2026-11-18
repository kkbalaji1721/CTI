"""Lab 6.2 - Try It Yourself
Covered Query and FETCH Stage Verification.

A covered query is a query where all fields required by the
query and projection are available in an index.
"""

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))

for path in (project_root, os.path.dirname(project_root)):
    if path and path not in sys.path:
        sys.path.insert(0, path)

from config.connection import get_db, banner


def find_stage(stage, stage_name):
    """Recursively search for a particular stage."""

    if not isinstance(stage, dict):
        return False

    if stage.get("stage") == stage_name:
        return True

    for key in ["inputStage", "inputStages", "outerStage", "innerStage"]:

        value = stage.get(key)

        if isinstance(value, dict):
            if find_stage(value, stage_name):
                return True

        elif isinstance(value, list):

            for item in value:
                if find_stage(item, stage_name):
                    return True

    return False


def main():

    banner("Lab 6.2: Try It Yourself - Covered Query")

    # ---------------------------------------------------------
    # CONNECT TO DATABASE
    # ---------------------------------------------------------

    db = get_db("nosql_labs")

    # Use the collection created in Lab 6.2
    col = db["perf_5_indexes"]

    print(f"[OK] Connected to collection: {col.name}")
    print(
        f"[OK] Documents in collection: "
        f"{col.count_documents({})}\n"
    )

    # ---------------------------------------------------------
    # CHECK EXISTING INDEX
    # ---------------------------------------------------------

    print("=== Checking Indexes ===")

    indexes = list(col.list_indexes())

    for index in indexes:

        print(
            f"  {index['name']:25} "
            f"keys={index['key']}"
        )

    # ---------------------------------------------------------
    # CREATE INDEX IF IT DOES NOT EXIST
    # ---------------------------------------------------------

    index_names = [
        index["name"]
        for index in indexes
    ]

    if "idx_sensor" not in index_names:

        print("\nCreating sensor_id index...")

        col.create_index(
            [("sensor_id", 1)],
            name="idx_sensor"
        )

        print("[OK] idx_sensor created.")

    else:

        print("\n[OK] idx_sensor already exists.")

    # ---------------------------------------------------------
    # COVERED QUERY
    # ---------------------------------------------------------

    print("\n=== Covered Query ===")

    query = {
        "sensor_id": "SENSOR-0050"
    }

    projection = {
        "_id": 0,
        "sensor_id": 1
    }

    print(f"Query      : {query}")
    print(f"Projection : {projection}")

    # Run the covered query
    results = list(
        col.find(
            query,
            projection
        )
    )

    print(
        f"\n[OK] Query returned "
        f"{len(results)} document(s)."
    )

    if results:
        print("Sample result:")
        print(results[0])

    # ---------------------------------------------------------
    # EXPLAIN THE COVERED QUERY
    # ---------------------------------------------------------

    print("\n=== EXPLAIN: Covered Query ===")

    try:
        explain_result = col.find(query, projection).explain()
    except TypeError:
        explain_result = db.command(
            "explain",
            {
                "find": col.name,
                "filter": query,
                "projection": projection,
            }
        )

    winning_plan = (
        explain_result
        .get("queryPlanner", {})
        .get("winningPlan", {})
    )

    print("\nWinning Plan:")
    print(winning_plan)

    # ---------------------------------------------------------
    # CHECK FOR FETCH STAGE
    # ---------------------------------------------------------

    execution_stats = explain_result.get(
        "executionStats",
        {}
    )

    execution_stage = execution_stats.get(
        "executionStages",
        {}
    )

    fetch_found = find_stage(
        execution_stage,
        "FETCH"
    )

    ixscan_found = find_stage(
        execution_stage,
        "IXSCAN"
    )

    docs_examined = execution_stats.get(
        "totalDocsExamined",
        "N/A"
    )

    keys_examined = execution_stats.get(
        "totalKeysExamined",
        "N/A"
    )

    print("\n=== Covered Query Verification ===")

    print(
        f"  IXSCAN stage found : {ixscan_found}"
    )

    print(
        f"  FETCH stage found  : {fetch_found}"
    )

    print(
        f"  Keys examined     : {keys_examined}"
    )

    print(
        f"  Documents examined: {docs_examined}"
    )

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------

    print("\n=== Result ===")

    if ixscan_found and not fetch_found:

        print(
            "[SUCCESS] This is a COVERED QUERY."
        )

        print(
            "[SUCCESS] FETCH stage is eliminated."
        )

        print(
            "[SUCCESS] The query is satisfied "
            "directly using the index."
        )

    elif fetch_found:

        print(
            "[INFO] FETCH stage is present."
        )

        print(
            "The query is not fully covered by "
            "the selected index."
        )

    else:

        print(
            "[INFO] Could not detect the stages "
            "from the execution plan."
        )

    # ---------------------------------------------------------
    # FINAL INDEX LIST
    # ---------------------------------------------------------

    print("\n=== Final Indexes ===")

    for index in col.list_indexes():

        print(
            f"  {index['name']:25} "
            f"keys={index['key']}"
        )

    banner("Lab 6.2 Try It Yourself Complete")


if __name__ == "__main__":
    main()