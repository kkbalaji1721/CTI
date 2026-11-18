import os
from pymongo import MongoClient, UpdateOne


# ---------------------------------------------------------
# 1. CONNECT TO MONGODB
# ---------------------------------------------------------

client = MongoClient(os.getenv("MONGO_URI"))

db = client["inventory"]
products = db["products"]


# ---------------------------------------------------------
# 2. PRODUCTS TO IMPORT
# ---------------------------------------------------------

product_data = [
    {
        "sku": "P001",
        "name": "Wireless Headphones",
        "price": 45,
        "stock": 25,
        "tags": ["electronics", "wireless"]
    },
    {
        "sku": "P002",
        "name": "Smart Watch",
        "price": 120,
        "stock": 15,
        "tags": ["electronics", "wireless", "premium"]
    },
    {
        "sku": "P003",
        "name": "Bluetooth Speaker",
        "price": 35,
        "stock": 0,
        "tags": ["electronics", "wireless"]
    },
    {
        "sku": "P004",
        "name": "Gaming Laptop",
        "price": 999,
        "stock": 8,
        "tags": ["electronics", "gaming", "premium"]
    },
    {
        "sku": "P005",
        "name": "Wireless Mouse",
        "price": 25,
        "stock": 50,
        "tags": ["electronics", "wireless"]
    }
]


# ---------------------------------------------------------
# 3. IDEMPOTENT BULK IMPORT FUNCTION
# ---------------------------------------------------------

def bulk_import_products(products_collection, products_to_import):

    operations = []

    for product in products_to_import:

        operations.append(
            UpdateOne(
                # Unique identifier used to find the document
                {"sku": product["sku"]},

                # Replace/update the product fields
                {"$set": product},

                # Insert if SKU does not already exist
                upsert=True
            )
        )

    if operations:
        result = products_collection.bulk_write(operations)

        print("Bulk import completed.")
        print(f"Inserted: {result.upserted_count}")
        print(f"Updated: {result.modified_count}")
        print(f"Matched: {result.matched_count}")


# ---------------------------------------------------------
# 4. RUN IMPORT
# ---------------------------------------------------------

print("=" * 60)
print("FIRST IMPORT")
print("=" * 60)

bulk_import_products(products, product_data)


# ---------------------------------------------------------
# 5. RUN IMPORT AGAIN
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("SECOND IMPORT")
print("=" * 60)

bulk_import_products(products, product_data)


# ---------------------------------------------------------
# 6. CHECK TOTAL DOCUMENTS
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("FINAL RESULT")
print("=" * 60)

print(
    f"Total products in collection: "
    f"{products.count_documents({})}"
)


# ---------------------------------------------------------
# CLOSE CONNECTION
# ---------------------------------------------------------

client.close()