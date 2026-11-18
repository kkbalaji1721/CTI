"""
Lab 4.2 - Implement Upsert and Bulk Operations

Conditional inserts + batch modifications.
"""

import sys
import os

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from pymongo import UpdateOne
from config.connection import get_db, reset_collection, banner


# ---------------------------------------------------------
# 1. SAMPLE PRODUCTS
# ---------------------------------------------------------

PRODUCTS = [
    {
        "sku": "A",
        "name": "Product A",
        "price": 100,
        "stock": 50,
        "is_active": True
    },
    {
        "sku": "B",
        "name": "Product B",
        "price": 200,
        "stock": 75,
        "is_active": True
    },
    {
        "sku": "C",
        "name": "Product C",
        "price": 300,
        "stock": 100,
        "is_active": True
    },
    {
        "sku": "D",
        "name": "Product D",
        "price": 400,
        "stock": 25,
        "is_active": True
    },
    {
        "sku": "E",
        "name": "Product E",
        "price": 500,
        "stock": 30,
        "is_active": True
    }
]


# ---------------------------------------------------------
# 2. UPSERT FUNCTION
# ---------------------------------------------------------

def upsert_product(col, sku, price):
    """
    If SKU exists, update its price.
    If SKU does not exist, insert a new product
    with default values.
    """

    result = col.update_one(
        {"sku": sku},

        {
            "$set": {
                "price": price
            },

            "$setOnInsert": {
                "sku": sku,
                "name": "New Product",
                "stock": 0,
                "is_active": True
            }
        },

        upsert=True
    )

    if result.matched_count:
        print(
            f"[UPDATED] SKU={sku} "
            f"(price updated to {price})"
        )

    elif result.upserted_id:
        print(
            f"[INSERTED] SKU={sku} "
            f"(new product created)"
        )

    return result


# ---------------------------------------------------------
# 3. MAIN PROGRAM
# ---------------------------------------------------------

def main():

    banner("Lab 4.2: Upsert and Bulk Operations")

    # Connect to database
    db = get_db("nosql_labs")

    # Reset inventory collection
    col = reset_collection(
        db,
        "inventory"
    )

    # Insert initial products
    col.insert_many(PRODUCTS)

    print(
        f"[OK] Inserted {len(PRODUCTS)} products.\n"
    )


    # -----------------------------------------------------
    # 4. UPSERT - EXISTING SKU
    # -----------------------------------------------------

    print(
        "=== Upsert: Existing SKU ==="
    )

    upsert_product(
        col,
        "A",
        150
    )

    doc = col.find_one(
        {"sku": "A"},
        {"_id": 0}
    )

    print(f"Result: {doc}")


    # -----------------------------------------------------
    # 5. UPSERT - NEW SKU
    # -----------------------------------------------------

    print(
        "\n=== Upsert: New SKU ==="
    )

    upsert_product(
        col,
        "F",
        600
    )

    doc = col.find_one(
        {"sku": "F"},
        {"_id": 0}
    )

    print(f"Result: {doc}")


    # -----------------------------------------------------
    # 6. BULK WRITE - 5 OPERATIONS
    # -----------------------------------------------------

    print(
        "\n=== Bulk Write: 5 operations ==="
    )

    operations = [

        # Product A: increase stock by 10
        UpdateOne(
            {"sku": "A"},
            {"$inc": {"stock": 10}}
        ),

        # Product B: increase stock by 10
        UpdateOne(
            {"sku": "B"},
            {"$inc": {"stock": 10}}
        ),

        # Product C: increase stock by 10
        UpdateOne(
            {"sku": "C"},
            {"$inc": {"stock": 10}}
        ),

        # Product D: deactivate
        UpdateOne(
            {"sku": "D"},
            {"$set": {"is_active": False}}
        ),

        # Product E: deactivate
        UpdateOne(
            {"sku": "E"},
            {"$set": {"is_active": False}}
        )
    ]


    # Execute all five operations
    bulk_result = col.bulk_write(
        operations
    )


    # -----------------------------------------------------
    # 7. VERIFY BULK WRITE RESULT
    # -----------------------------------------------------

    print("\n=== Bulk Write Result ===")

    print(
        f"Matched:   {bulk_result.matched_count}"
    )

    print(
        f"Modified:  {bulk_result.modified_count}"
    )

    print(
        f"Upserted:  {bulk_result.upserted_count}"
    )

    print(
        f"Upserted IDs: {bulk_result.upserted_ids}"
    )


    # -----------------------------------------------------
    # 8. FINAL INVENTORY
    # -----------------------------------------------------

    print(
        "\n=== Final Inventory ==="
    )

    for doc in col.find(
        {},
        {"_id": 0}
    ).sort("sku"):

        print(
            f"{doc['sku']} | "
            f"{doc['name']} | "
            f"Price={doc['price']} | "
            f"Stock={doc['stock']} | "
            f"Active={doc['is_active']}"
        )


    # -----------------------------------------------------
    # 9. COMPLETE
    # -----------------------------------------------------

    banner("Lab 4.2 Complete")


if __name__ == "__main__":
    main()