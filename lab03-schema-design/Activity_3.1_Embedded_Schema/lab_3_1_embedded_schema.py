"""
Lab 3.1 - Design an Embedded Document Schema
============================================
Course enrollment system for a university.

What this script does
---------------------
1. Creates a `courses` collection with an embedded roster of students
   (name, student id, grade) and an embedded schedule (days, time, room).
2. Adds JSON Schema validation that REQUIRES title, code, instructor
   and schedule.
3. Inserts 3 course documents.
4. Queries all courses that meet on Monday.
5. Queries all students enrolled in courses taught by a given instructor.
6. Media requirement: stores a PHOTO (course banner) directly inside the
   document as BSON Binary, and stores a MINI VIDEO in GridFS and keeps
   only its ObjectId reference inside the document.

Run:  python lab_3_1_embedded_schema.py
Needs a MongoDB server on mongodb://localhost:27017 (or set MONGO_URI).
"""

import os
import sys
from pathlib import Path

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError, WriteError
from bson import json_util

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from media_utils import build_photo_fields, store_video_gridfs, rebuild_image_from_fields

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "nosql_lab3"


def banner(text):
    print("\n" + "=" * 68)
    print(text)
    print("=" * 68)


def get_db():
    """Connect to MongoDB and fail with a clear message if it is not running."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        print(f"[ERROR] Cannot reach MongoDB at {MONGO_URI}.")
        print("        Start the server (mongod) and run this script again.")
        sys.exit(1)
    print(f"[OK] Connected to MongoDB at {MONGO_URI} (database: {DB_NAME})")
    return client[DB_NAME]


def export_json(collection, filename, limit=None):
    """Export a collection to a .json file (mongoexport style, pretty printed)."""
    cursor = collection.find()
    if limit:
        cursor = cursor.limit(limit)
    docs = list(cursor)
    out = HERE / filename
    out.write_text(json_util.dumps(docs, indent=2), encoding="utf-8")
    print(f"[OK] Exported {len(docs)} document(s) -> {out.name}")


# ----------------------------------------------------------------------
# 2. Schema validation rules
#    title, code, instructor and schedule are REQUIRED.
# ----------------------------------------------------------------------
COURSE_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "Course document validation",
        "required": ["title", "code", "instructor", "schedule"],
        "properties": {
            "title": {
                "bsonType": "string",
                "minLength": 3,
                "description": "Course title - required string",
            },
            "code": {
                "bsonType": "string",
                "pattern": r"^[A-Z]{2,4}[0-9]{3}$",
                "description": "Course code like CS401 - required",
            },
            "instructor": {
                "bsonType": "string",
                "description": "Instructor name - required string",
            },
            "credits": {"bsonType": "int", "minimum": 1, "maximum": 6},
            "schedule": {
                "bsonType": "object",
                "required": ["days", "time", "room"],
                "description": "Embedded schedule sub-document - required",
                "properties": {
                    "days": {
                        "bsonType": "array",
                        "minItems": 1,
                        "items": {"bsonType": "string"},
                    },
                    "time": {"bsonType": "string"},
                    "room": {"bsonType": "string"},
                },
            },
            "roster": {
                "bsonType": "array",
                "description": "Embedded array of enrolled students",
                "items": {
                    "bsonType": "object",
                    "required": ["student_id", "name"],
                    "properties": {
                        "student_id": {"bsonType": "string"},
                        "name": {"bsonType": "string"},
                        "grade": {"bsonType": ["string", "null"]},
                    },
                },
            },
            "photo_width": {"bsonType": ["int", "null"]},
            "photo_height": {"bsonType": ["int", "null"]},
            "photo_channels": {"bsonType": ["int", "null"]},
            "photo_pixels": {"bsonType": ["binData", "null"], "description": "Raw pixel bytes"},
            "photo_description": {"bsonType": ["string", "null"]},
            "intro_video_id": {"bsonType": ["objectId", "null"]},
        },
    }
}

# ----------------------------------------------------------------------
# 1. The embedded schema - roster and schedule live INSIDE the course
# ----------------------------------------------------------------------
COURSES = [
    {
        "title": "Database Systems",
        "code": "CS401",
        "instructor": "Dr. Priya Sharma",
        "credits": 4,
        "schedule": {"days": ["Monday", "Wednesday"], "time": "10:00-11:30", "room": "LH-201"},
        "roster": [
            {"student_id": "24BTRCL076", "name": "Gowni Pranay", "grade": "A"},
            {"student_id": "24BTRCL011", "name": "Arjun Mehta", "grade": "A-"},
            {"student_id": "24BTRCL034", "name": "Sneha Reddy", "grade": "B+"},
            {"student_id": "24BTRCL052", "name": "Divya Patel", "grade": "B"},
        ],
    },
    {
        "title": "Machine Learning",
        "code": "AIML301",
        "instructor": "Dr. Anil Gupta",
        "credits": 3,
        "schedule": {"days": ["Tuesday", "Thursday"], "time": "14:00-15:30", "room": "LH-305"},
        "roster": [
            {"student_id": "24BTRCL076", "name": "Gowni Pranay", "grade": "A+"},
            {"student_id": "24BTRCL018", "name": "Kavya Nair", "grade": "A"},
            {"student_id": "24BTRCL045", "name": "Vikram Singh", "grade": None},
        ],
    },
    {
        "title": "Natural Language Processing",
        "code": "AIML201",
        "instructor": "Dr. Priya Sharma",
        "credits": 3,
        "schedule": {"days": ["Monday", "Friday"], "time": "09:00-10:00", "room": "LH-102"},
        "roster": [
            {"student_id": "24BTRCL034", "name": "Sneha Reddy", "grade": "B+"},
            {"student_id": "24BTRCL067", "name": "Rahul Kumar", "grade": None},
            {"student_id": "24BTRCL029", "name": "Priya Das", "grade": "A-"},
        ],
    },
]


def load_media(db):
    """Return (photo_fields dict, video_file_id). Photo is stored as pixel data
    + a text description, video is referenced from GridFS."""
    photo_fields = build_photo_fields(prefix="photo")
    video_id = store_video_gridfs(db, bucket_name="fs")
    return photo_fields, video_id


def main():
    banner("LAB 3.1 - EMBEDDED DOCUMENT SCHEMA (COURSE ENROLLMENT)")
    db = get_db()

    # --- media (photo + mini video) -----------------------------------
    print("\n--- Step 0: media files ---")
    photo_fields, video_id = load_media(db)

    # --- create collection with validation ----------------------------
    print("\n--- Step 1: create 'courses' collection with schema validation ---")
    if "courses" in db.list_collection_names():
        db.drop_collection("courses")
    db.create_collection("courses", validator=COURSE_VALIDATOR)
    courses = db["courses"]
    courses.create_index([("code", ASCENDING)], unique=True)
    courses.create_index([("schedule.days", ASCENDING)])
    courses.create_index([("instructor", ASCENDING)])
    print("[OK] Collection created. Required fields: title, code, instructor, schedule")

    # --- insert course documents --------------------------------------
    print("\n--- Step 2: insert 3 course documents ---")
    docs = []
    for course in COURSES:
        doc = dict(course)
        doc.update(photo_fields)             # PHOTO stored as pixel data + description
        doc["intro_video_id"] = video_id     # MINI VIDEO referenced from GridFS
        docs.append(doc)
    result = courses.insert_many(docs)
    print(f"[OK] Inserted {len(result.inserted_ids)} courses")
    for c in courses.find({}, {"code": 1, "title": 1, "roster": 1, "_id": 0}):
        print(f"    {c['code']:8} {c['title']:32} roster={len(c['roster'])} students")

    # --- Query A: courses that meet on Monday --------------------------
    print("\n--- Step 3: QUERY - all courses that meet on Monday ---")
    print('    db.courses.find({"schedule.days": "Monday"})')
    for c in courses.find({"schedule.days": "Monday"},
                          {"code": 1, "title": 1, "schedule": 1, "_id": 0}):
        s = c["schedule"]
        print(f"    {c['code']:8} {c['title']:32} {', '.join(s['days']):22} {s['time']} @ {s['room']}")

    # --- Query B: students taught by a specific instructor -------------
    target = "Dr. Priya Sharma"
    print(f"\n--- Step 4: QUERY - all students in courses taught by {target} ---")
    pipeline = [
        {"$match": {"instructor": target}},
        {"$unwind": "$roster"},
        {"$group": {
            "_id": {"student_id": "$roster.student_id", "name": "$roster.name"},
            "courses": {"$addToSet": "$code"},
        }},
        {"$sort": {"_id.name": 1}},
    ]
    for row in courses.aggregate(pipeline):
        info = row["_id"]
        print(f"    {info['student_id']:12} {info['name']:16} -> {', '.join(sorted(row['courses']))}")

    # simple version without aggregation (distinct student names)
    names = courses.distinct("roster.name", {"instructor": target})
    print(f"    distinct() shortcut: {len(names)} students -> {', '.join(sorted(names))}")

    # --- Step 5: prove the validator works ----------------------------
    print("\n--- Step 5: schema validation test (missing 'instructor' + 'schedule') ---")
    try:
        courses.insert_one({"title": "Broken Course", "code": "CS999"})
        print("    [ERROR] Document was accepted - validation is NOT working!")
    except WriteError as e:
        print("    [OK] Rejected by validator, as expected.")
        print(f"    Reason: {str(e)[:110]}...")

    # --- Step 6: embedded update (add one student with $push) ----------
    print("\n--- Step 6: add a student to CS401 using $push (single atomic write) ---")
    courses.update_one(
        {"code": "CS401"},
        {"$push": {"roster": {"student_id": "24BTRCL088", "name": "Amit Verma", "grade": None}}},
    )
    print(f"    CS401 roster size is now {len(courses.find_one({'code': 'CS401'})['roster'])}")

    # --- Step 7: media read-back --------------------------------------
    print("\n--- Step 7: read the media back out of MongoDB ---")
    doc = courses.find_one({"code": "CS401"})
    if doc.get("photo_pixels") is not None:
        arr = rebuild_image_from_fields(doc, prefix="photo")
        print(f"    Photo rebuilt from stored pixels: shape={arr.shape}")
        print(f"    Description: {doc['photo_description']}")
    if doc.get("intro_video_id") is not None:
        import gridfs
        gout = gridfs.GridFS(db).get(doc["intro_video_id"])
        print(f"    GridFS video read back : {gout.filename}, {gout.length} bytes, {gout.content_type}")

    # --- export -------------------------------------------------------
    print("\n--- Step 8: export collection to JSON ---")
    export_json(courses, "courses.json")

    banner("LAB 3.1 COMPLETE")


if __name__ == "__main__":
    main()
