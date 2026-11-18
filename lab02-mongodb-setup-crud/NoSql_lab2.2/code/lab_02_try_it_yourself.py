
"""
Lab 2.2 - Try It Yourself

Bookstore CRUD Operations

Additional requirement:
Increase the price of all books published before 2010
by 10 percent.

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

    documents = list(collection.find({}))

    # Convert MongoDB ObjectId to string
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

    banner(
        "Lab 2.2 Try It Yourself: Bookstore CRUD"
    )

    # Connect to MongoDB
    db = get_db("bookstore_try_it")

    # Reset collection
    collection = reset_collection(
        "bookstore_try_it",
        "books"
    )

    # -----------------------------------------------------
    # CREATE
    # -----------------------------------------------------

    books = [

        {
            "title": "Python Crash Course",
            "author": "Eric Matthes",
            "year": 2023,
            "genre": "Programming",
            "price": 45.99,
            "tags": [
                "Python",
                "programming",
                "beginner"
            ]
        },

        {
            "title": "Data Science from Scratch",
            "author": "Joel Grus",
            "year": 2022,
            "genre": "Data Science",
            "price": 39.99,
            "tags": [
                "Python",
                "data-science",
                "AI"
            ]
        },

        {
            "title": "Learning SQL",
            "author": "Alan Beaulieu",
            "year": 2009,
            "genre": "Database",
            "price": 42.50,
            "tags": [
                "SQL",
                "database"
            ]
        },

        {
            "title": "Artificial Intelligence Basics",
            "author": "Tom Taulli",
            "year": 2024,
            "genre": "Artificial Intelligence",
            "price": 55.00,
            "tags": [
                "AI",
                "machine-learning"
            ]
        },

        {
            "title": "Clean Architecture",
            "author": "Robert C. Martin",
            "year": 2017,
            "genre": "Programming",
            "price": 48.99,
            "tags": [
                "programming",
                "software"
            ]
        }
    ]

    print("=== CREATE: Inserting 5 books ===")

    result = collection.insert_many(books)

    print(
        f"[OK] Inserted {len(result.inserted_ids)} books"
    )

    # -----------------------------------------------------
    # READ 1
    # -----------------------------------------------------

    print(
        "\n=== READ: Books published after 2021 ==="
    )

    books_after_2021 = collection.find(
        {"year": {"$gt": 2021}}
    )

    for book in books_after_2021:

        print(
            f"{book['title']} "
            f"({book['year']}) - "
            f"${book['price']:.2f}"
        )

    # -----------------------------------------------------
    # READ 2
    # -----------------------------------------------------

    print(
        "\n=== READ: Programming books ==="
    )

    programming_books = collection.find(
        {"genre": "Programming"}
    )

    for book in programming_books:

        print(
            f"{book['title']} - "
            f"{book['author']}"
        )

    # -----------------------------------------------------
    # READ 3
    # -----------------------------------------------------

    print(
        "\n=== READ: Books priced $40-$50 ==="
    )

    price_books = collection.find(
        {
            "price": {
                "$gte": 40,
                "$lte": 50
            }
        }
    )

    for book in price_books:

        print(
            f"{book['title']} - "
            f"${book['price']:.2f}"
        )

    # -----------------------------------------------------
    # READ 4
    # -----------------------------------------------------

    print(
        "\n=== READ: Books tagged 'Python' ==="
    )

    python_books = collection.find(
        {"tags": "Python"}
    )

    for book in python_books:

        print(
            f"{book['title']} - "
            f"{book['tags']}"
        )

    # -----------------------------------------------------
    # UPDATE 1
    # -----------------------------------------------------

    print(
        "\n=== UPDATE: Increase all prices by 10% ==="
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

    for book in collection.find({}):

        print(
            f"{book['title']} - "
            f"${book['price']:.2f}"
        )

    # -----------------------------------------------------
    # UPDATE 2 - PROFESSOR'S REQUIREMENT
    # -----------------------------------------------------

    print(
        "\n=== UPDATE: Increase prices of books "
        "published before 2010 by 10% ==="
    )

    # Get books before update
    old_books = list(
        collection.find(
            {
                "year": {
                    "$lt": 2010
                }
            }
        )
    )

    result = collection.update_many(
        {
            "year": {
                "$lt": 2010
            }
        },
        {
            "$mul": {
                "price": 1.10
            }
        }
    )

    print(
        f"[OK] Updated {result.modified_count} "
        f"book(s) published before 2010"
    )

    # Verify the update
    for old_book in old_books:

        new_book = collection.find_one(
            {"_id": old_book["_id"]}
        )

        print(
            f"{new_book['title']} "
            f"({new_book['year']}) : "
            f"${old_book['price']:.2f} "
            f"-> ${new_book['price']:.2f}"
        )

    # -----------------------------------------------------
    # UPDATE 3 - CHANGE GENRE
    # -----------------------------------------------------

    print(
        "\n=== UPDATE: Change genre ==="
    )

    result = collection.update_one(
        {
            "title": "Learning SQL"
        },
        {
            "$set": {
                "genre": "SQL Database"
            }
        }
    )

    print(
        f"[OK] Updated {result.modified_count} book(s)"
    )

    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------

    print(
        "\n=== DELETE: Remove Clean Architecture ==="
    )

    result = collection.delete_one(
        {
            "title": "Clean Architecture"
        }
    )

    print(
        f"[OK] Deleted {result.deleted_count} book(s)"
    )

    # -----------------------------------------------------
    # FINAL COLLECTION
    # -----------------------------------------------------

    print(
        "\n=== FINAL COLLECTION ==="
    )

    final_books = collection.find({})

    for book in final_books:

        print(
            f"{book['title']} - "
            f"${book['price']:.2f}"
        )

    # -----------------------------------------------------
    # SAVE JSON
    # -----------------------------------------------------

    save_collection_json(
        collection,
        "lab_02_try_it_yourself.json"
    )

    banner(
        "Lab 2.2 Try It Yourself Complete!"
    )


if __name__ == "__main__":
    main()

