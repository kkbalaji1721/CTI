import os
from pymongo import MongoClient


# ---------------------------------------------------------
# 1. CONNECT TO MONGODB
# ---------------------------------------------------------

client = MongoClient(os.getenv("MONGO_URI"))

db = client["inventory"]
products = db["products"]


# ---------------------------------------------------------
# 2. SAMPLE PRODUCTS
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

# Clear old data
products.delete_many({})

# Insert products
products.insert_many(product_data)

print("=" * 60)
print("PRODUCTS INSERTED")
print("=" * 60)
print(f"Inserted {len(product_data)} products.")


# ---------------------------------------------------------
# 3. REGEX TEXT SEARCH FUNCTION
# ---------------------------------------------------------

def search_products(search_string):

    results = products.find(
        {
            "name": {
                "$regex": search_string,
                "$options": "i"
            }
        },
        {
            "_id": 0,
            "sku": 1,
            "name": 1,
            "price": 1,
            "stock": 1
        }
    )

    return list(results)


# ---------------------------------------------------------
# 4. TEST SEARCH
# ---------------------------------------------------------

search_string = "wireless"

print("\n" + "=" * 60)
print(f"SEARCH RESULTS FOR: '{search_string}'")
print("=" * 60)

results = search_products(search_string)

for product in results:
    print(
        f"{product['sku']} - "
        f"{product['name']} - "
        f"Price: {product['price']} - "
        f"Stock: {product['stock']}"
    )


# ---------------------------------------------------------
# 5. TEST CASE-INSENSITIVE SEARCH
# ---------------------------------------------------------

search_string = "LAPTOP"

print("\n" + "=" * 60)
print(f"SEARCH RESULTS FOR: '{search_string}'")
print("=" * 60)

results = search_products(search_string)

for product in results:
    print(
        f"{product['sku']} - "
        f"{product['name']} - "
        f"Price: {product['price']} - "
        f"Stock: {product['stock']}"
    )


# ---------------------------------------------------------
# 6. CLOSE CONNECTION
# ---------------------------------------------------------

client.close()