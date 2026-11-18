import os
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid


# ---------------------------------------------------------
# 1. CONNECTION
# ---------------------------------------------------------

client = MongoClient(os.getenv("MONGO_URI"))

db = client["inventory"]


# ---------------------------------------------------------
# 2. CREATE PRODUCTS COLLECTION WITH SCHEMA VALIDATION
# ---------------------------------------------------------

# Remove old collection if it already exists
if "products" in db.list_collection_names():
    db.products.drop()

validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "price", "stock", "tags"],
        "properties": {

            "name": {
                "bsonType": "string",
                "description": "Name must be a string"
            },

            "price": {
                "bsonType": ["int", "long", "double", "decimal"],
                "minimum": 0,
                "description": "Price must be a positive number"
            },

            "stock": {
                "bsonType": "int",
                "minimum": 0,
                "description": "Stock must be a non-negative integer"
            },

            "tags": {
                "bsonType": "array",
                "items": {
                    "bsonType": "string"
                },
                "description": "Tags must be an array of strings"
            }
        }
    }
}


db.create_collection(
    "products",
    validator=validator,
    validationLevel="strict",
    validationAction="error"
)

products = db["products"]


# ---------------------------------------------------------
# 3. INSERT AT LEAST 10 PRODUCTS
# ---------------------------------------------------------

product_data = [
    {
        "name": "Wireless Headphones",
        "price": 45,
        "stock": 25,
        "tags": ["electronics", "wireless"]
    },
    {
        "name": "Smart Watch",
        "price": 120,
        "stock": 15,
        "tags": ["electronics", "wireless", "premium"]
    },
    {
        "name": "Bluetooth Speaker",
        "price": 35,
        "stock": 0,
        "tags": ["electronics", "wireless"]
    },
    {
        "name": "Gaming Laptop",
        "price": 999,
        "stock": 8,
        "tags": ["electronics", "gaming", "premium"]
    },
    {
        "name": "Wireless Mouse",
        "price": 25,
        "stock": 50,
        "tags": ["electronics", "wireless"]
    },
    {
        "name": "Mechanical Keyboard",
        "price": 75,
        "stock": 20,
        "tags": ["electronics", "wireless", "gaming"]
    },
    {
        "name": "Office Chair",
        "price": 150,
        "stock": 0,
        "tags": ["furniture", "office"]
    },
    {
        "name": "USB Cable",
        "price": 10,
        "stock": 100,
        "tags": ["electronics", "cable"]
    },
    {
        "name": "Premium Monitor",
        "price": 300,
        "stock": 12,
        "tags": ["electronics", "premium"]
    },
    {
        "name": "Desk Lamp",
        "price": 30,
        "stock": 40,
        "tags": ["home", "lighting"]
    }
]

result = products.insert_many(product_data)

print("=" * 60)
print("INSERT OPERATION")
print("=" * 60)
print(f"Inserted {len(result.inserted_ids)} products.")


# ---------------------------------------------------------
# 4. COMPARISON OPERATORS
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("COMPARISON OPERATORS")
print("=" * 60)

# Products with price between 20 and 50
print("\nProducts with price between 20 and 50:")

results = products.find({
    "price": {
        "$gte": 20,
        "$lte": 50
    }
})

for product in results:
    print(
        f"{product['name']} - "
        f"Price: {product['price']} - "
        f"Stock: {product['stock']}"
    )


# Products with stock equal to 0
print("\nOut-of-stock products:")

results = products.find({
    "stock": {
        "$eq": 0
    }
})

for product in results:
    print(
        f"{product['name']} - "
        f"Price: {product['price']}"
    )


# ---------------------------------------------------------
# 5. LOGICAL OPERATORS
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("LOGICAL OPERATORS")
print("=" * 60)


# Out of stock OR price above 100
print("\nOut of stock OR priced above 100:")

results = products.find({
    "$or": [
        {"stock": 0},
        {"price": {"$gt": 100}}
    ]
})

for product in results:
    print(
        f"{product['name']} - "
        f"Price: {product['price']} - "
        f"Stock: {product['stock']}"
    )


# In stock AND tagged as premium
print("\nIn stock AND tagged as premium:")

results = products.find({
    "$and": [
        {"stock": {"$gt": 0}},
        {"tags": "premium"}
    ]
})

for product in results:
    print(
        f"{product['name']} - "
        f"Stock: {product['stock']} - "
        f"Tags: {product['tags']}"
    )


# ---------------------------------------------------------
# 6. ARRAY OPERATORS
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("ARRAY OPERATORS")
print("=" * 60)


# Products having BOTH electronics AND wireless
print("\nProducts with BOTH 'electronics' AND 'wireless':")

results = products.find({
    "tags": {
        "$all": ["electronics", "wireless"]
    }
})

for product in results:
    print(
        f"{product['name']} - "
        f"Tags: {product['tags']}"
    )


# Products with exactly 2 tags
print("\nProducts with exactly 2 tags:")

results = products.find({
    "tags": {
        "$size": 2
    }
})

for product in results:
    print(
        f"{product['name']} - "
        f"Tags: {product['tags']}"
    )


# ---------------------------------------------------------
# 7. PAGINATION FUNCTION
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("PAGINATION")
print("=" * 60)


def get_products_page(page_number, items_per_page):
    """
    Returns products for the requested page.

    Products are sorted alphabetically by name.
    """

    if page_number < 1:
        raise ValueError("Page number must be at least 1")

    if items_per_page < 1:
        raise ValueError("Items per page must be at least 1")

    skip_count = (page_number - 1) * items_per_page

    results = (
        products
        .find({}, {"_id": 0})
        .sort("name", 1)
        .skip(skip_count)
        .limit(items_per_page)
    )

    return list(results)


# Example: Page 1, 3 products per page
page_number = 1
items_per_page = 3

page = get_products_page(page_number, items_per_page)

print(
    f"\nPage {page_number} "
    f"({items_per_page} products per page):"
)

for product in page:
    print(
        f"{product['name']} - "
        f"Price: {product['price']} - "
        f"Stock: {product['stock']}"
    )


# Example: Page 2
page_number = 2

page = get_products_page(page_number, items_per_page)

print(
    f"\nPage {page_number} "
    f"({items_per_page} products per page):"
)

for product in page:
    print(
        f"{product['name']} - "
        f"Price: {product['price']} - "
        f"Stock: {product['stock']}"
    )


# ---------------------------------------------------------
# 8. UPDATE OPERATION
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("UPDATE OPERATION")
print("=" * 60)

update_result = products.update_one(
    {"name": "Wireless Mouse"},
    {
        "$set": {
            "price": 30
        },
        "$inc": {
            "stock": 10
        }
    }
)

print(f"Documents modified: {update_result.modified_count}")


# ---------------------------------------------------------
# 9. DELETE OPERATION
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("DELETE OPERATION")
print("=" * 60)

delete_result = products.delete_one({
    "name": "USB Cable"
})

print(f"Documents deleted: {delete_result.deleted_count}")


# ---------------------------------------------------------
# 10. FINAL COUNT
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("FINAL RESULT")
print("=" * 60)

print(
    f"Total products remaining: "
    f"{products.count_documents({})}"
)


# ---------------------------------------------------------
# CLOSE CONNECTION
# ---------------------------------------------------------

client.close()