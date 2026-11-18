"""Lab 1.1 - Try It Yourself
Research and classify additional database products into NoSQL families."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.connection import get_db, reset_collection, banner
from rich.table import Table
from rich.console import Console

console = Console()


def main():
    banner("Lab 1.1: Try It Yourself - Additional Database Products")

    db = get_db("nosql_labs")
    col = reset_collection("nosql_labs", "try_database_products")

    # 10 additional real-world database products classified into NoSQL families
    products = [
        {"name": "ScyllaDB", "family": "Wide-Column", "data_model": "Column-Family",
         "vendor": "ScyllaDB Inc.", "use_case": "IoT, gaming, real-time applications", "open_source": True},

        {"name": "InfluxDB", "family": "Time-Series", "data_model": "Time-Series",
         "vendor": "InfluxData", "use_case": "IoT monitoring, metrics, sensor data", "open_source": True},

        {"name": "ArangoDB", "family": "Multi-Model", "data_model": "Document / Graph / Key-Value",
         "vendor": "ArangoDB", "use_case": "Knowledge graphs, recommendations, connected data", "open_source": True},

        {"name": "CouchDB", "family": "Document", "data_model": "JSON Document",
         "vendor": "Apache", "use_case": "Offline-first applications and data synchronization", "open_source": True},

        {"name": "DynamoDB", "family": "Key-Value / Document", "data_model": "Key-Value / Document",
         "vendor": "AWS", "use_case": "Shopping carts, serverless applications, session management", "open_source": False},

        {"name": "Neo4j", "family": "Graph", "data_model": "Labeled Property Graph",
         "vendor": "Neo4j Inc.", "use_case": "Knowledge graphs, fraud detection, recommendations", "open_source": True},

        {"name": "OrientDB", "family": "Multi-Model", "data_model": "Document / Graph",
         "vendor": "OrientDB", "use_case": "Connected applications and graph-based data", "open_source": True},

        {"name": "Aerospike", "family": "Key-Value", "data_model": "Key-Value",
         "vendor": "Aerospike Inc.", "use_case": "Real-time bidding, fraud detection, personalization", "open_source": True},

        {"name": "Dgraph", "family": "Graph", "data_model": "Distributed Graph",
         "vendor": "Dgraph Labs", "use_case": "Knowledge graphs and connected data applications", "open_source": True},

        {"name": "RethinkDB", "family": "Document", "data_model": "JSON Document",
         "vendor": "RethinkDB", "use_case": "Real-time applications and live data feeds", "open_source": True},
    ]

    col.insert_many(products)
    print(f"[OK] Inserted {len(products)} additional database products.\n")

    # Print a rich table
    table = Table(title="Try It Yourself - NoSQL Database Product Survey", show_lines=True)
    table.add_column("Product", style="cyan", width=16)
    table.add_column("Family", style="magenta", width=18)
    table.add_column("Data Model", width=30)
    table.add_column("Use Case", width=45)

    for p in col.find().sort("family"):
        table.add_row(
            p["name"],
            p["family"],
            p["data_model"],
            p["use_case"]
        )

    console.print(table)

    # Group by family
    print("\n--- Grouped by Family ---")
    pipeline = [
        {
            "$group": {
                "_id": "$family",
                "count": {"$sum": 1},
                "products": {"$push": "$name"}
            }
        },
        {
            "$sort": {
                "count": -1
            }
        }
    ]

    for group in col.aggregate(pipeline):
        print(
            f"  {group['_id']:20} : "
            f"{group['count']} products -> "
            f"{', '.join(group['products'])}"
        )

    # Identify products that span multiple families
    print("\n--- Multi-Model / Multiple Family Products ---")

    multi_model = col.find({
        "$or": [
            {"family": "Multi-Model"},
            {"family": {"$regex": "/"}}
        ]
    })

    for product in multi_model:
        print(
            f"  {product['name']} -> "
            f"{product['family']}"
        )

    print("\nThese products span multiple NoSQL families or data models.")

    # Interactive: classify 3 mystery products
    print("\n--- Interactive Classification ---")
    print("Classify these 3 additional products into a NoSQL family:")

    mystery = [
        {
            "name": "Redis",
            "hint": "In-memory database commonly used for caching and real-time applications"
        },
        {
            "name": "MongoDB",
            "hint": "Document database that stores flexible BSON documents"
        },
        {
            "name": "Apache Cassandra",
            "hint": "Distributed database designed for large-scale column-family data"
        }
    ]

    answers = {
        "Redis": "Key-Value",
        "MongoDB": "Document",
        "Apache Cassandra": "Wide-Column"
    }

    for m in mystery:
        print(f"  {m['name']}: {m['hint']}")

    print(f"\nExpected answers: {answers}")

    # Conclusion
    print("\n--- Conclusion ---")
    print("Some database products fit neatly into one NoSQL family.")
    print("Some products support multiple data models.")
    print("ArangoDB and OrientDB are examples of multi-model databases.")
    print("DynamoDB supports both key-value and document data models.")
    print("InfluxDB is specialized for time-series workloads.")

    banner("Lab 1.1 Try It Yourself Complete")


if __name__ == "__main__":
    main()