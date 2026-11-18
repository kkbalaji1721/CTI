"""Lab 1.2 - Try It Yourself
Map data domains of additional real-world applications to appropriate NoSQL families."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.connection import get_db, reset_collection, banner
from rich.table import Table
from rich.console import Console

console = Console()


def main():
    banner("Lab 1.2: Try It Yourself - Map Application Data Domains to NoSQL Families")

    db = get_db("nosql_labs")
    col = reset_collection("nosql_labs", "try_app_domain_mapping")

    # --- E-Commerce Application ---
    print("=== E-Commerce Application ===")
    ecommerce_domains = [
        {
            "app": "E-Commerce",
            "domain": "customer_profiles",
            "description": "Customer details, addresses, preferences, and account information",
            "read_write_pattern": "Read-heavy, occasional updates",
            "recommended_family": "Document",
            "recommended_db": "MongoDB",
            "rationale": "Flexible JSON documents can store customer information with nested addresses and preferences"
        },
        {
            "app": "E-Commerce",
            "domain": "product_catalog",
            "description": "Products, categories, specifications, prices, and product attributes",
            "read_write_pattern": "Read-heavy with frequent product updates",
            "recommended_family": "Document",
            "recommended_db": "MongoDB",
            "rationale": "Products can have different attributes and fit naturally into flexible documents"
        },
        {
            "app": "E-Commerce",
            "domain": "shopping_cart",
            "description": "Active shopping carts containing products, quantities, and prices",
            "read_write_pattern": "Very frequent reads and writes",
            "recommended_family": "Key-Value",
            "recommended_db": "Redis",
            "rationale": "Fast key-based access makes Redis suitable for frequently changing shopping carts"
        },
        {
            "app": "E-Commerce",
            "domain": "product_reviews",
            "description": "Customer reviews, ratings, comments, and review timestamps",
            "read_write_pattern": "Write-heavy with frequent reads",
            "recommended_family": "Document",
            "recommended_db": "MongoDB",
            "rationale": "Reviews have flexible fields and can be stored efficiently as JSON-like documents"
        },
    ]

    # --- Healthcare Monitoring Application ---
    print("=== Healthcare Monitoring Application ===")
    healthcare_domains = [
        {
            "app": "Healthcare Monitoring",
            "domain": "patient_relationships",
            "description": "Relationships between patients, doctors, hospitals, and medical specialists",
            "read_write_pattern": "Relationship and traversal queries",
            "recommended_family": "Graph",
            "recommended_db": "Neo4j",
            "rationale": "Graph databases efficiently represent and traverse relationships between healthcare entities"
        },
        {
            "app": "Healthcare Monitoring",
            "domain": "patient_vitals",
            "description": "Heart rate, blood pressure, temperature, and other sensor readings over time",
            "read_write_pattern": "High-volume time-series writes and range queries",
            "recommended_family": "Time-Series",
            "recommended_db": "InfluxDB",
            "rationale": "InfluxDB is designed for storing and querying large amounts of time-series sensor data"
        },
        {
            "app": "Healthcare Monitoring",
            "domain": "medical_records",
            "description": "Patient medical history, diagnoses, prescriptions, and treatment information",
            "read_write_pattern": "Read-heavy with structured and flexible records",
            "recommended_family": "Document",
            "recommended_db": "MongoDB",
            "rationale": "Document storage supports flexible medical records with nested information"
        },
        {
            "app": "Healthcare Monitoring",
            "domain": "live_device_status",
            "description": "Current status of connected medical monitoring devices",
            "read_write_pattern": "Frequent updates and fast lookups",
            "recommended_family": "Key-Value",
            "recommended_db": "Redis",
            "rationale": "Redis provides fast key-based reads and writes for real-time device status"
        },
    ]

    all_domains = ecommerce_domains + healthcare_domains
    col.insert_many(all_domains)

    print(f"[OK] Inserted {len(all_domains)} domain mappings.\n")

    # Print tables per application
    for app_name in ["E-Commerce", "Healthcare Monitoring"]:
        table = Table(
            title=f"{app_name} - Data Domain Mapping",
            show_lines=True
        )

        table.add_column("Domain", width=22)
        table.add_column("Description", width=55)
        table.add_column("NoSQL Family", width=16)
        table.add_column("Recommended DB", width=22)
        table.add_column("Key Rationale", width=48)

        for d in col.find({"app": app_name}):
            table.add_row(
                d["domain"],
                d["description"],
                d["recommended_family"],
                d["recommended_db"],
                d["rationale"]
            )

        console.print(table)
        print()

    # Summary: family distribution
    print("--- Family Distribution ---")

    pipeline = [
        {
            "$group": {
                "_id": "$recommended_family",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "count": -1
            }
        }
    ]

    for g in col.aggregate(pipeline):
        print(f"  {g['_id']:20} : {g['count']} domain(s)")

    banner("Lab 1.2 Try It Yourself Complete")


if __name__ == "__main__":
    main()