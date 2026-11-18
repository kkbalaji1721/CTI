"""
Lab 3.2 - Migrate from Referenced to Embedded Design
====================================================
Blog system: posts + comments.

What this script does
---------------------
1. REFERENCED design: separate `posts` and `comments` collections.
   Inserts 5 posts and 10 comments (comments hold a post_id reference).
2. Retrieves a post together with its comments in ONE query using $lookup.
3. EMBEDDED design: comments become an array inside the post document.
   The data is migrated with an aggregation pipeline ($lookup + $merge).
4. Compares how many database round-trips each design needs to render a
   post page, and times both.

Media requirement: every post carries a cover PHOTO embedded as BSON
Binary, and the MINI VIDEO is stored once in GridFS with only its
ObjectId referenced from the post - large binaries are referenced, small
ones are embedded.

Run:  python lab_3_2_migrate_referenced_to_embedded.py
"""

import os
import sys
import time
from pathlib import Path

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError
from bson import json_util
import gridfs

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


POSTS = [
    {"slug": "why-nosql", "title": "Why NoSQL Matters for AI", "author": "pranay",
     "tags": ["nosql", "ai"], "created": "2026-01-15"},
    {"slug": "aggregation-tips", "title": "MongoDB Aggregation Tips", "author": "sneha",
     "tags": ["mongodb", "aggregation"], "created": "2026-01-20"},
    {"slug": "vector-search", "title": "Vector Search Deep Dive", "author": "kavya",
     "tags": ["vector", "ai", "search"], "created": "2026-02-01"},
    {"slug": "cap-theorem", "title": "CAP Theorem Explained", "author": "arjun",
     "tags": ["cap", "distributed"], "created": "2026-02-10"},
    {"slug": "graph-fraud", "title": "Graph Databases for Fraud Detection", "author": "rahul",
     "tags": ["graph", "fraud"], "created": "2026-02-15"},
]

# 10 comments spread over the 5 posts (post index, author, text)
COMMENTS = [
    (0, "reader_a", "Great overview, very clear."),
    (0, "reader_b", "Bookmarked this for my exam."),
    (0, "reader_c", "Could you add a SQL comparison table?"),
    (1, "reader_d", "$facet deserves a follow-up post."),
    (1, "reader_a", "The $lookup example finally made sense."),
    (2, "reader_e", "How does HNSW compare with IVF here?"),
    (2, "reader_b", "Nice, practical writeup."),
    (3, "reader_f", "AP systems are underrated."),
    (3, "reader_c", "Useful for interviews too."),
    (4, "reader_g", "A real fraud case study would help."),
]


def load_media(db):
    photo_fields = build_photo_fields(prefix="cover_photo")
    video_id = store_video_gridfs(db, bucket_name="blog_media")
    return photo_fields, video_id


def main():
    banner("LAB 3.2 - REFERENCED vs EMBEDDED BLOG DESIGN")
    db = get_db()

    print("\n--- Step 0: media files ---")
    photo_fields, video_id = load_media(db)

    # ================= PART A: REFERENCED DESIGN =====================
    print("\n--- Step 1: PART A - referenced design (posts + comments) ---")
    for name in ("posts", "comments", "posts_embedded"):
        db.drop_collection(name)
    posts = db["posts"]
    comments = db["comments"]

    post_docs = []
    for p in POSTS:
        d = dict(p)
        d.update(photo_fields)           # photo stored as pixel data + description
        d["video_id"] = video_id         # large binary -> referenced (GridFS)
        post_docs.append(d)
    post_ids = posts.insert_many(post_docs).inserted_ids
    print(f"[OK] Inserted {len(post_ids)} posts into 'posts'")

    comment_docs = [
        {"post_id": post_ids[i], "author": author, "text": text, "likes": 0}
        for i, author, text in COMMENTS
    ]
    comments.insert_many(comment_docs)
    comments.create_index([("post_id", ASCENDING)])
    print(f"[OK] Inserted {len(comment_docs)} comments into 'comments' (indexed on post_id)")

    # ---- the naive way: 2 round-trips ----
    print("\n--- Step 2: reading a post + its comments the NAIVE way (2 queries) ---")
    t0 = time.perf_counter()
    one_post = posts.find_one({"slug": "why-nosql"})            # query 1
    its_comments = list(comments.find({"post_id": one_post["_id"]}))  # query 2
    naive_ms = (time.perf_counter() - t0) * 1000
    print(f"    '{one_post['title']}' + {len(its_comments)} comments")
    print(f"    round-trips = 2, time = {naive_ms:.2f} ms")

    # ---- the $lookup way: 1 round-trip ----
    print("\n--- Step 3: same result in ONE query using $lookup ---")
    lookup_pipeline = [
        {"$match": {"slug": "why-nosql"}},
        {"$lookup": {
            "from": "comments",
            "localField": "_id",
            "foreignField": "post_id",
            "as": "comments",
        }},
        {"$project": {"_id": 0, "title": 1, "author": 1, "comments.author": 1,
                      "comments.text": 1}},
    ]
    t0 = time.perf_counter()
    joined = list(posts.aggregate(lookup_pipeline))
    lookup_ms = (time.perf_counter() - t0) * 1000
    doc = joined[0]
    print(f"    {doc['title']} (by {doc['author']}) -> {len(doc['comments'])} comments")
    for c in doc["comments"]:
        print(f"        {c['author']:10} : {c['text']}")
    print(f"    round-trips = 1 ($lookup does the join server-side), time = {lookup_ms:.2f} ms")

    # ================= PART B: MIGRATION =============================
    print("\n--- Step 4: PART B - migrate to the EMBEDDED design ---")
    print("    Aggregation pipeline: $lookup -> $addFields -> $project -> $merge")
    migration = [
        {"$lookup": {
            "from": "comments",
            "localField": "_id",
            "foreignField": "post_id",
            "as": "comments",
        }},
        {"$addFields": {
            "comment_count": {"$size": "$comments"},
            # drop the redundant post_id from every embedded comment
            "comments": {
                "$map": {
                    "input": "$comments",
                    "as": "c",
                    "in": {"author": "$$c.author", "text": "$$c.text", "likes": "$$c.likes"},
                }
            },
        }},
        {"$merge": {"into": "posts_embedded", "whenMatched": "replace",
                    "whenNotMatched": "insert"}},
    ]
    posts.aggregate(migration)
    posts_embedded = db["posts_embedded"]
    print(f"[OK] Migrated {posts_embedded.count_documents({})} posts into 'posts_embedded'")

    print("\n--- Step 5: verify the migration ---")
    src_comments = comments.count_documents({})
    moved = list(posts_embedded.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$comment_count"}}}
    ]))[0]["total"]
    print(f"    comments in referenced design : {src_comments}")
    print(f"    comments inside embedded docs : {moved}")
    print(f"    match: {'YES' if src_comments == moved else 'NO'}")
    for p in posts_embedded.find({}, {"_id": 0, "slug": 1, "comment_count": 1}).sort("slug", 1):
        print(f"    {p['slug']:18} -> {p['comment_count']} embedded comments")

    # ---- read the embedded post: 1 round-trip, no join ----
    print("\n--- Step 6: reading a post + comments from the EMBEDDED design ---")
    t0 = time.perf_counter()
    emb = posts_embedded.find_one({"slug": "why-nosql"})   # query 1, no join
    emb_ms = (time.perf_counter() - t0) * 1000
    print(f"    {emb['title']} -> {len(emb['comments'])} comments")
    for c in emb["comments"]:
        print(f"        {c['author']:10} : {c['text']}")
    print(f"    round-trips = 1 (plain find_one, no join), time = {emb_ms:.2f} ms")

    # media survived the migration
    if emb.get("cover_photo_pixels") is not None:
        arr = rebuild_image_from_fields(emb, prefix="cover_photo")
        print(f"    cover photo rebuilt from pixels: shape={arr.shape}")
        print(f"    description: {emb['cover_photo_description']}")
    if emb.get("video_id") is not None:
        gf = gridfs.GridFS(db, collection="blog_media").get(emb["video_id"])
        print(f"    mini video still referenced: {gf.filename}, {gf.length} bytes")

    # ================= COMPARISON ====================================
    print("\n--- Step 7: query-count comparison to display one post page ---")
    rows = [
        ("Referenced - naive app code", "2 queries (find post, find comments)", f"{naive_ms:.2f} ms"),
        ("Referenced - $lookup", "1 query (server-side join)", f"{lookup_ms:.2f} ms"),
        ("Embedded", "1 query (no join at all)", f"{emb_ms:.2f} ms"),
    ]
    print(f"    {'Design':<30}{'DB round-trips':<40}{'Time'}")
    print("    " + "-" * 82)
    for a, b, c in rows:
        print(f"    {a:<30}{b:<40}{c}")

    print(f"""
    Trade-offs
      Referenced : comments are independent, unbounded and easy to page or
                   moderate; needs a join or a second query for every read.
      Embedded   : one disk read gives the whole page, no join; but the post
                   document grows with every comment and the 16 MB BSON limit
                   is a hard ceiling (see the 'Try it yourself' activity).""")

    print("\n--- Step 8: export ---")
    export_json(posts, "posts.json")
    export_json(comments, "comments.json")
    export_json(posts_embedded, "posts_embedded.json")

    banner("LAB 3.2 COMPLETE")


if __name__ == "__main__":
    main()
