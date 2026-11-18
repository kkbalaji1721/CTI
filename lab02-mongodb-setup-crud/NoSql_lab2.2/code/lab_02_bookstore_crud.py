
"""
Lab 2.2 - Bookstore CRUD Operations

CREATE:
    Insert 5 books

READ:
    Books published after 2020
    Machine Learning books
    Books priced $40-$60
    Books tagged 'AI'

UPDATE:
    Increase all book prices by 10%

DELETE:
    Remove 'Clean Code'

The final MongoDB collection is also saved as JSON.
"""

import os
import sys
import json

# Allow Python to find config folder
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from config.connection import (
    get_db,
    reset_collection,
    banner
)


# ---------------------------------------------------------
# SAVE COLLECTION AS JSON
# ---------------------------------------------------------

def save_collection_json(collection, filename):

    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    json_file = os.path.join(
        base_dir,
        filename
    )

    documents = list(collection.find())

    # Convert ObjectId into string
    for document in documents:
        document["_id"] = str(document["_id"])

    with open(
        json_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            documents,
            file,
            indent=4,
            default=str
        )

    print()
    print("[OK] JSON file saved:")
    print(json_file)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    banner("Lab 2.2: Bookstore CRUD Operations")

    # Connect to MongoDB
    db = get_db("bookstore_lab")

    # Reset collection
    collection = reset_collection(
        "bookstore_lab",
        "books"
    )

    # -----------------------------------------------------
    # CREATE
    # -----------------------------------------------------

    books = [

        {
            "title": "The Pragmatic Programmer",
            "author": "Andrew Hunt",
            "year": 1999,
            "genre": "Programming",
            "price": 49.99,
            "tags": ["programming", "software"]
        },

        {
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "year": 2017,
            "genre": "Database",
            "price": 45.99,
            "tags": ["database", "distributed-systems"]
        },

        {
            "title": "Deep Learning",
            "author": "Ian Goodfellow, Yoshua Bengio, Aaron Courville",
            "year": 2016,
            "genre": "Machine Learning",
            "price": 72.00,
            "tags": ["AI", "neural-networks", "theory"]
        },

        {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "year": 2008,
            "genre": "Programming",
            "price": 39.99,
            "tags": ["programming", "software-engineering"]
        },

        {
            "title": "Hands-On Machine Learning",
            "author": "Aurelien Geron",
            "year": 2022,
            "genre": "Machine Learning",
            "price": 59.99,
            "tags": ["AI", "scikit-learn", "tensorflow", "practical"]
        }
    ]

    print("=== CREATE: Inserting 5 books ===")

    result = collection.insert_many(books)

    print(f"[OK] Inserted {len(result.inserted_ids)} books")

    # -----------------------------------------------------
    # READ 1
    # -----------------------------------------------------

    print("\n=== READ: Books published after 2020 ===")

    books_after_2020 = collection.find(
        {"year": {"$gt": 2020}}
    )

    for book in books_after_2020:

        print(
            f"  {book['title']:45}"
            f" ({book['year']}) - ${book['price']:.2f}"
        )

    # -----------------------------------------------------
    # READ 2
    # -----------------------------------------------------

    print("\n=== READ: Machine Learning books ===")

    ml_books = collection.find(
        {"genre": "Machine Learning"}
    )

    for book in ml_books:

        print(
            f"  {book['title']:45}"
            f" by {book['author']}"
        )

    # -----------------------------------------------------
    # READ 3
    # -----------------------------------------------------

    print("\n=== READ: Books priced $40-$60 ===")

    price_books = collection.find(
        {
            "price": {
                "$gte": 40,
                "$lte": 60
            }
        }
    )

    for book in price_books:

        print(
            f"  {book['title']:45}"
            f" ${book['price']:.2f}"
        )

    # -----------------------------------------------------
    # READ 4
    # -----------------------------------------------------

    print("\n=== READ: Books tagged 'AI' ===")

    ai_books = collection.find(
        {"tags": "AI"}
    )

    for book in ai_books:

        print(
            f"  {book['title']:45}"
            f" tags: {book['tags']}"
        )

    # -----------------------------------------------------
    # UPDATE
    # -----------------------------------------------------

    print("\n=== UPDATE: 10% price increase ===")

    books_before_update = list(
        collection.find({})
    )

    result = collection.update_many(
        {},
        {
            "$mul": {
                "price": 1.10
            }
        }
    )

    print(
        f"[OK] Updated {result.modified_count} books"
    )

    for old_book in books_before_update:

        new_book = collection.find_one(
            {"_id": old_book["_id"]}
        )

        print(
            f"  {old_book['title']:45}"
            f" ${old_book['price']:.2f}"
            f" -> ${new_book['price']:.2f}"
        )

    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------

    print("\n=== DELETE: Removing 'Clean Code' ===")

    result = collection.delete_one(
        {"title": "Clean Code"}
    )

    print(
        f"[OK] Deleted {result.deleted_count} document(s)"
    )

    remaining = collection.count_documents({})

    print(
        f"  Remaining books: {remaining}"
    )

    # -----------------------------------------------------
    # FINAL COLLECTION
    # -----------------------------------------------------

    print("\n=== Final Collection State ===")

    final_books = collection.find({})

    for book in final_books:

        print(
            f"  {book['title']}"
        )

    # -----------------------------------------------------
    # SAVE JSON
    # -----------------------------------------------------

    save_collection_json(
        collection,
        "lab_02_bookstore_crud.json"
    )

    banner("Lab 2.2 Complete")


if __name__ == "__main__":
    main()

