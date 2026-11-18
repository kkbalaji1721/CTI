"""
Lab 3.1 - Try It Yourself: Track prerequisites between courses
==============================================================
Requirement: add prerequisite relationships between courses and justify
whether they should be EMBEDDED or REFERENCED.

DECISION (implemented below): a HYBRID - reference by course code, with a
small cached copy of the title inside the parent course document.

    "prerequisites": [ {"code": "CS201", "title": "Data Structures"} ]

Why:
  * A prerequisite IS another course document. Fully embedding the whole
    prerequisite course would duplicate its roster, schedule and banner
    photo in every course that requires it - and every edit to that course
    would then have to be applied in many places.
  * Prerequisite lists are tiny and bounded (0-3 entries), so keeping the
    codes inside the parent course means the common query
    ("what do I need before CS401?") is answered by a single find() with
    no join at all.
  * The cached title makes the list printable without a join; the code is
    the real link, so titles can be refreshed with one update when needed.
  * Prerequisites form a GRAPH (chains: CS101 -> CS201 -> CS401). Because
    we store a reference, MongoDB's $graphLookup can walk the whole chain
    recursively - impossible if we had embedded copies.

Media requirement: the photo is embedded as BSON Binary (course banner)
and the mini video is stored in GridFS and referenced by ObjectId - the
same embed-vs-reference trade-off applied to binary data.

Run:  python lab_3_1_try_prerequisites.py
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

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "nosql_lab3"


def banner(text):
    print("\n" + "=" * 68)
    print(text)
    print("=" * 68)


def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        print(f"[ERROR] Cannot reach MongoDB at {MONGO_URI}. Start mongod and retry.")
        sys.exit(1)
    print(f"[OK] Connected to MongoDB at {MONGO_URI} (database: {DB_NAME})")
    return client[DB_NAME]


def export_json(collection, filename):
    docs = list(collection.find())
    out = HERE / filename
    out.write_text(json_util.dumps(docs, indent=2), encoding="utf-8")
    print(f"[OK] Exported {len(docs)} document(s) -> {out.name}")


CATALOG_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["title", "code", "instructor", "schedule"],
        "properties": {
            "title": {"bsonType": "string"},
            "code": {"bsonType": "string", "pattern": r"^[A-Z]{2,4}[0-9]{3}$"},
            "instructor": {"bsonType": "string"},
            "schedule": {
                "bsonType": "object",
                "required": ["days", "time", "room"],
                "properties": {
                    "days": {"bsonType": "array", "items": {"bsonType": "string"}},
                    "time": {"bsonType": "string"},
                    "room": {"bsonType": "string"},
                },
            },
            "prerequisites": {
                "bsonType": "array",
                "description": "Referenced prerequisites (course code + cached title)",
                "items": {
                    "bsonType": "object",
                    "required": ["code"],
                    "properties": {
                        "code": {"bsonType": "string"},
                        "title": {"bsonType": "string"},
                    },
                },
            },
            "photo_width": {"bsonType": ["int", "null"]},
            "photo_height": {"bsonType": ["int", "null"]},
            "photo_channels": {"bsonType": ["int", "null"]},
            "photo_pixels": {"bsonType": ["binData", "null"]},
            "photo_description": {"bsonType": ["string", "null"]},
            "intro_video_id": {"bsonType": ["objectId", "null"]},
        },
    }
}

# Prerequisite chain:  CS101 -> CS201 -> CS401 -> AIML301
#                      CS101 -> AIML201
CATALOG = [
    {
        "title": "Programming Fundamentals", "code": "CS101",
        "instructor": "Dr. Meera Joshi", "credits": 4,
        "schedule": {"days": ["Monday", "Thursday"], "time": "08:00-09:30", "room": "LH-001"},
        "prerequisites": [],
    },
    {
        "title": "Data Structures", "code": "CS201",
        "instructor": "Dr. Meera Joshi", "credits": 4,
        "schedule": {"days": ["Tuesday", "Friday"], "time": "11:00-12:30", "room": "LH-104"},
        "prerequisites": [{"code": "CS101", "title": "Programming Fundamentals"}],
    },
    {
        "title": "Database Systems", "code": "CS401",
        "instructor": "Dr. Priya Sharma", "credits": 4,
        "schedule": {"days": ["Monday", "Wednesday"], "time": "10:00-11:30", "room": "LH-201"},
        "prerequisites": [{"code": "CS201", "title": "Data Structures"}],
    },
    {
        "title": "Machine Learning", "code": "AIML301",
        "instructor": "Dr. Anil Gupta", "credits": 3,
        "schedule": {"days": ["Tuesday", "Thursday"], "time": "14:00-15:30", "room": "LH-305"},
        "prerequisites": [
            {"code": "CS401", "title": "Database Systems"},
            {"code": "CS201", "title": "Data Structures"},
        ],
    },
    {
        "title": "Natural Language Processing", "code": "AIML201",
        "instructor": "Dr. Priya Sharma", "credits": 3,
        "schedule": {"days": ["Monday", "Friday"], "time": "09:00-10:00", "room": "LH-102"},
        "prerequisites": [{"code": "CS101", "title": "Programming Fundamentals"}],
    },
]


def load_media(db):
    photo_fields = build_photo_fields(prefix="photo")
    video_id = store_video_gridfs(db, bucket_name="catalog_media")
    return photo_fields, video_id


def main():
    banner("LAB 3.1 TRY IT YOURSELF - COURSE PREREQUISITES (REFERENCED)")
    db = get_db()

    print("\n--- Step 0: media files ---")
    photo_fields, video_id = load_media(db)

    print("\n--- Step 1: create 'course_catalog' with prerequisite support ---")
    if "course_catalog" in db.list_collection_names():
        db.drop_collection("course_catalog")
    db.create_collection("course_catalog", validator=CATALOG_VALIDATOR)
    catalog = db["course_catalog"]
    catalog.create_index([("code", ASCENDING)], unique=True)
    catalog.create_index([("prerequisites.code", ASCENDING)])
    print("[OK] Collection created with validator + index on prerequisites.code")

    docs = []
    for c in CATALOG:
        d = dict(c)
        d.update(photo_fields)
        d["intro_video_id"] = video_id
        docs.append(d)
    catalog.insert_many(docs)
    print(f"[OK] Inserted {len(docs)} courses into the catalog")

    print("\n--- Step 2: direct prerequisites (0 joins - they are in the document) ---")
    for c in catalog.find({}, {"code": 1, "title": 1, "prerequisites": 1, "_id": 0}).sort("code", 1):
        pre = ", ".join(p["code"] for p in c["prerequisites"]) or "none"
        print(f"    {c['code']:8} {c['title']:30} requires: {pre}")

    print("\n--- Step 3: resolve one level with $lookup (code -> full course doc) ---")
    pipeline = [
        {"$match": {"code": "AIML301"}},
        {"$lookup": {
            "from": "course_catalog",
            "localField": "prerequisites.code",
            "foreignField": "code",
            "as": "prereq_details",
        }},
        {"$project": {
            "_id": 0, "code": 1, "title": 1,
            "prereq_details.code": 1, "prereq_details.title": 1,
            "prereq_details.instructor": 1,
        }},
    ]
    for row in catalog.aggregate(pipeline):
        print(f"    {row['code']} - {row['title']}")
        for p in row["prereq_details"]:
            print(f"        <- {p['code']:8} {p['title']:28} ({p['instructor']})")

    print("\n--- Step 4: full prerequisite CHAIN with $graphLookup (recursive) ---")
    chain = [
        {"$match": {"code": "AIML301"}},
        {"$graphLookup": {
            "from": "course_catalog",
            "startWith": "$prerequisites.code",
            "connectFromField": "prerequisites.code",
            "connectToField": "code",
            "as": "all_prereqs",
            "depthField": "level",
        }},
        {"$project": {"_id": 0, "code": 1, "all_prereqs.code": 1,
                      "all_prereqs.title": 1, "all_prereqs.level": 1}},
    ]
    for row in catalog.aggregate(chain):
        print(f"    Everything needed before {row['code']}:")
        for p in sorted(row["all_prereqs"], key=lambda x: x["level"]):
            print(f"        depth {p['level']}: {p['code']:8} {p['title']}")

    print("\n--- Step 5: reverse question - which courses does CS201 unlock? ---")
    for c in catalog.find({"prerequisites.code": "CS201"}, {"code": 1, "title": 1, "_id": 0}):
        print(f"    CS201 -> {c['code']:8} {c['title']}")

    print("\n--- Step 6: eligibility check for a student ---")
    completed = {"CS101", "CS201"}
    print(f"    Student 24BTRCL076 has completed: {', '.join(sorted(completed))}")
    for c in catalog.find({}, {"code": 1, "title": 1, "prerequisites": 1, "_id": 0}).sort("code", 1):
        needed = {p["code"] for p in c["prerequisites"]}
        missing = needed - completed
        status = "ELIGIBLE" if not missing else f"blocked (needs {', '.join(sorted(missing))})"
        print(f"    {c['code']:8} {status}")

    print("\n--- Step 7: cheap title refresh (one write, because we referenced) ---")
    catalog.update_one({"code": "CS201"}, {"$set": {"title": "Data Structures & Algorithms"}})
    catalog.update_many({"prerequisites.code": "CS201"},
                        {"$set": {"prerequisites.$[p].title": "Data Structures & Algorithms"}},
                        array_filters=[{"p.code": "CS201"}])
    for c in catalog.find({"prerequisites.code": "CS201"}, {"code": 1, "prerequisites": 1, "_id": 0}):
        print(f"    {c['code']} now shows: {[p['title'] for p in c['prerequisites']]}")

    print("\n--- Step 8: validator still active (bad prerequisite entry) ---")
    try:
        catalog.insert_one({
            "title": "Bad Course", "code": "CS777", "instructor": "Nobody",
            "schedule": {"days": ["Monday"], "time": "10:00", "room": "X"},
            "prerequisites": [{"title": "missing code field"}],
        })
        print("    [ERROR] Should have been rejected!")
    except WriteError as e:
        print(f"    [OK] Rejected: {str(e)[:100]}...")

    print("\n--- Step 9: media read-back ---")
    one = catalog.find_one({"code": "CS401"})
    if one.get("photo_pixels") is not None:
        arr = rebuild_image_from_fields(one, prefix="photo")
        print(f"    Photo rebuilt from stored pixels: shape={arr.shape}")
        print(f"    Description: {one['photo_description']}")

    print("\n--- Step 10: export ---")
    export_json(catalog, "course_catalog.json")

    print("""
JUSTIFICATION (summary)
    Embed  -> schedule + roster: small, always read with the course, never
              shared with another course.
    Reference -> prerequisites: a prerequisite is a full course that many
              other courses point at; duplicating it would multiply data and
              multiply updates. A tiny cached title keeps reads join-free
              while $graphLookup can still walk the whole chain.
    Same rule for media: the small PHOTO is embedded, the larger VIDEO is
              stored once in GridFS and only referenced.""")

    banner("LAB 3.1 TRY IT YOURSELF COMPLETE")


if __name__ == "__main__":
    main()
