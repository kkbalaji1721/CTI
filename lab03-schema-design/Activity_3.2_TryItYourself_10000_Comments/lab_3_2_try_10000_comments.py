"""
Lab 3.2 - Try It Yourself: a post with 10,000 comments
======================================================
Question: why is embedding a bad idea here, and what would you use instead?

ANSWER (demonstrated by this script)
------------------------------------
Why embedding breaks down at 10,000 comments:
  1. HARD LIMIT - a BSON document can never exceed 16 MB. This script
     measures the real average comment size and prints how many comments
     fit before the document is refused by the server.
  2. WHOLE-DOCUMENT READS - MongoDB reads and returns the entire document.
     Showing the first 10 comments of a post still pulls all 10,000 into
     memory and over the network.
  3. DOCUMENT GROWTH - every $push rewrites/moves a document that keeps
     getting bigger, which fragments storage and slows writes.
  4. NO PAGING OR SORTING - "latest 20 comments" inside a huge array needs
     $slice tricks or an unwind; there is no index on array position.
  5. INDEX COST - an index on comments.author must store one entry per
     array element, so one post creates 10,000 index keys.
  6. CONTENTION - every new comment writes the same single document, so
     all commenters serialise on one document lock.

Better designs (both implemented below):
  A. REFERENCED - keep comments in their own collection with an index on
     {post_id, created}. Unbounded growth, easy paging, one small write
     per comment. This is the correct default.
  B. BUCKET / OUTLIER PATTERN - store comments in "pages" of 100 inside
     bucket documents. Reading a page is one document; writes append to
     the newest bucket only. This is the hybrid used when you want the
     locality of embedding without unbounded documents.
  C. Keep a small SUBSET embedded in the post (e.g. latest 10 preview
     comments) so the post page renders from one read, with the full
     thread loaded from B on demand.

Media requirement: the post keeps its PHOTO embedded as BSON Binary, and
the MINI VIDEO goes to GridFS - GridFS is itself the bucket pattern
applied to binary data (it splits a file into 255 KB chunk documents
exactly because one document cannot hold everything).

Run:  python lab_3_2_try_10000_comments.py
"""

import os
import sys
import time
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from bson import Binary, json_util
import bson
import gridfs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from media_utils import build_photo_fields, store_video_gridfs, rebuild_image_from_fields

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "nosql_lab3"

TOTAL_COMMENTS = 10_000
BUCKET_SIZE = 100
MAX_BSON = 16 * 1024 * 1024


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


def export_json(collection, filename, limit=None, note=""):
    cursor = collection.find()
    if limit:
        cursor = cursor.limit(limit)
    docs = list(cursor)
    out = HERE / filename
    out.write_text(json_util.dumps(docs, indent=2), encoding="utf-8")
    print(f"[OK] Exported {len(docs)} document(s) -> {out.name} {note}")


SENTENCES = [
    "This finally made the concept click for me.",
    "Could you cover the indexing side next?",
    "I hit the same problem in production last month.",
    "Nice writeup, sharing it with my team.",
    "The diagram is the best part of this post.",
    "Does this hold for sharded clusters too?",
    "Bookmarking this before my exam.",
    "Small typo in the third code block.",
    "Any benchmark numbers to back this up?",
    "Worked on MongoDB 7 exactly as described.",
]


def make_comments(n):
    random.seed(42)
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    out = []
    for i in range(n):
        out.append({
            "seq": i + 1,
            "author": f"user_{random.randint(1, 900):03d}",
            "text": random.choice(SENTENCES),
            "likes": random.randint(0, 40),
            "created": base + timedelta(minutes=i),
        })
    return out


def main():
    banner("LAB 3.2 TRY IT YOURSELF - 10,000 COMMENTS ON ONE POST")
    db = get_db()

    for name in ("viral_post", "viral_comments", "comment_buckets"):
        db.drop_collection(name)

    # --- the post itself, with photo as pixel data + video referenced --
    print("\n--- Step 0: the post, with its media ---")
    photo_fields = build_photo_fields(prefix="cover_photo")
    video_id = store_video_gridfs(db, bucket_name="viral_media")
    if video_id is not None:
        chunks = db["viral_media.chunks"].count_documents({"files_id": video_id})
        print(f"     video split into {chunks} chunk document(s)")
        print("     GridFS chunking IS the bucket pattern applied to binary data.")
    post = {
        "slug": "why-nosql-went-viral",
        "title": "Why NoSQL Went Viral",
        "author": "pranay",
        "video_id": video_id,        # large binary -> referenced
        "comment_count": 0,
        "recent_comments": [],       # design C: small embedded preview
    }
    post.update(photo_fields)        # photo stored as pixel data + description
    post_id = db["viral_post"].insert_one(post).inserted_id

    comments = make_comments(TOTAL_COMMENTS)

    # ================= WHY EMBEDDING BREAKS =========================
    print("\n--- Step 1: measure what 10,000 embedded comments would cost ---")
    one = bson.BSON.encode({"c": comments[0]})
    avg = len(bson.BSON.encode({"all": comments[:500]})) / 500
    total = avg * TOTAL_COMMENTS
    print(f"    size of one comment sub-document : ~{len(one)} bytes")
    print(f"    average encoded size per comment : ~{avg:.0f} bytes")
    print(f"    10,000 comments inside the post  : ~{total/1024:.0f} KB "
          f"({total/1024/1024:.2f} MB)")
    print(f"    BSON document limit              : {MAX_BSON/1024/1024:.0f} MB "
          f"= ~{int(MAX_BSON/avg):,} comments MAXIMUM, ever")
    photo_bytes = photo_fields.get("cover_photo_pixels")
    photo_note = f" plus a {len(photo_bytes)/1024:.0f} KB pixel-data photo" if photo_bytes else ""
    print(f"    the post also carries its own fields{photo_note}, so the real")
    print("    ceiling is lower - and every read of the post pays for all of it.")

    # prove the whole-document read cost
    fat = dict(post)
    fat.pop("_id", None)
    fat["comments"] = comments
    fat_size = len(bson.BSON.encode(fat))
    print(f"    a single 'fat' post document would encode to {fat_size/1024:.0f} KB;")
    print("    MongoDB returns the WHOLE document even if the page shows 10 comments.")

    # --- try the write MongoDB would actually reject -------------------
    print("\n--- Step 2: what happens if we push past the limit ---")
    try:
        oversized = {"_id": "too-big", "blob": Binary(b"x" * (MAX_BSON + 1024))}
        db["viral_post"].insert_one(oversized)
        print("    [ERROR] server accepted an oversized document?!")
    except Exception as e:   # DocumentTooLarge / OperationFailure
        print(f"    [OK] Rejected as expected: {type(e).__name__}: {str(e)[:90]}...")

    # ================= ALTERNATIVE A: REFERENCED ====================
    print("\n--- Step 3: alternative A - referenced comments (the default fix) ---")
    ref = db["viral_comments"]
    t0 = time.perf_counter()
    ref.insert_many([dict(c, post_id=post_id) for c in comments])
    ins_ms = (time.perf_counter() - t0) * 1000
    ref.create_index([("post_id", ASCENDING), ("created", DESCENDING)])
    print(f"    inserted {ref.count_documents({}):,} comment documents in {ins_ms:.0f} ms")
    t0 = time.perf_counter()
    page = list(ref.find({"post_id": post_id}).sort("created", DESCENDING).limit(20))
    page_ms = (time.perf_counter() - t0) * 1000
    print(f"    newest 20 comments fetched in {page_ms:.2f} ms "
          f"(index scan, {len(page)} docs, nothing else read)")
    print(f"    example: #{page[0]['seq']} {page[0]['author']} - {page[0]['text']}")

    # ================= ALTERNATIVE B: BUCKET PATTERN ================
    print(f"\n--- Step 4: alternative B - bucket pattern ({BUCKET_SIZE} comments per bucket) ---")
    buckets = db["comment_buckets"]
    docs = []
    for b in range(0, TOTAL_COMMENTS, BUCKET_SIZE):
        chunk = comments[b:b + BUCKET_SIZE]
        docs.append({
            "post_id": post_id,
            "bucket_no": b // BUCKET_SIZE,
            "count": len(chunk),
            "first_seq": chunk[0]["seq"],
            "last_seq": chunk[-1]["seq"],
            "comments": chunk,
        })
    t0 = time.perf_counter()
    buckets.insert_many(docs)
    bucket_ms = (time.perf_counter() - t0) * 1000
    buckets.create_index([("post_id", ASCENDING), ("bucket_no", DESCENDING)])
    sample = buckets.find_one({"bucket_no": 0})
    bucket_size_kb = len(bson.BSON.encode(sample)) / 1024
    print(f"    created {buckets.count_documents({})} bucket documents in {bucket_ms:.0f} ms")
    print(f"    each bucket is ~{bucket_size_kb:.0f} KB - far below the 16 MB limit")
    t0 = time.perf_counter()
    newest = buckets.find_one({"post_id": post_id}, sort=[("bucket_no", DESCENDING)])
    b_ms = (time.perf_counter() - t0) * 1000
    print(f"    newest page = 1 document read ({newest['count']} comments, "
          f"seq {newest['first_seq']}-{newest['last_seq']}) in {b_ms:.2f} ms")

    # appending a new comment: only the newest bucket is touched
    print("\n--- Step 5: appending a comment with the bucket pattern ---")
    new_comment = {"seq": TOTAL_COMMENTS + 1, "author": "user_new",
                   "text": "Adding one more comment.", "likes": 0,
                   "created": datetime.now(timezone.utc)}
    target = buckets.find_one({"post_id": post_id, "count": {"$lt": BUCKET_SIZE}},
                              sort=[("bucket_no", DESCENDING)])
    if target is None:
        buckets.insert_one({"post_id": post_id, "bucket_no": newest["bucket_no"] + 1,
                            "count": 1, "first_seq": new_comment["seq"],
                            "last_seq": new_comment["seq"], "comments": [new_comment]})
        print(f"    all buckets were full -> opened bucket #{newest['bucket_no'] + 1}")
    else:
        buckets.update_one({"_id": target["_id"]},
                           {"$push": {"comments": new_comment},
                            "$inc": {"count": 1},
                            "$set": {"last_seq": new_comment["seq"]}})
        print(f"    appended to bucket #{target['bucket_no']} (only that document was written)")

    # ================= ALTERNATIVE C: PREVIEW SUBSET ================
    print("\n--- Step 6: alternative C - keep a small preview inside the post ---")
    preview = [{"author": c["author"], "text": c["text"]} for c in comments[-5:]]
    db["viral_post"].update_one(
        {"_id": post_id},
        {"$set": {"recent_comments": preview, "comment_count": TOTAL_COMMENTS + 1}},
    )
    p = db["viral_post"].find_one({"_id": post_id}, {"comment_count": 1, "recent_comments": 1})
    print(f"    post now stores comment_count={p['comment_count']:,} and "
          f"{len(p['recent_comments'])} preview comments")
    print("    -> the post page renders from ONE read; the full thread is paged from buckets")

    full_post = db["viral_post"].find_one({"_id": post_id})
    if full_post.get("cover_photo_pixels") is not None:
        arr = rebuild_image_from_fields(full_post, prefix="cover_photo")
        print(f"    cover photo rebuilt from pixels: shape={arr.shape}")
        print(f"    description: {full_post['cover_photo_description']}")

    # ================= COMPARISON ===================================
    print("\n--- Step 7: comparison for a post with 10,000 comments ---")
    header = f"    {'Design':<22}{'Doc size':<14}{'Reads for 1 page':<20}{'Write cost':<24}{'Verdict'}"
    print(header)
    print("    " + "-" * 100)
    rows = [
        ("Fully embedded", f"~{fat_size/1024:.0f} KB", "1 (whole doc)", "rewrite huge doc",
         "FAILS at scale"),
        ("Referenced", "~200 B each", "1 indexed query", "1 tiny insert", "best default"),
        (f"Bucket ({BUCKET_SIZE}/doc)", f"~{bucket_size_kb:.0f} KB", "1 bucket doc",
         "append to 1 bucket", "best locality"),
        ("Preview + buckets", "post stays small", "1 for the page", "1 bucket + 1 $set",
         "best for UI"),
    ]
    for r in rows:
        print(f"    {r[0]:<22}{r[1]:<14}{r[2]:<20}{r[3]:<24}{r[4]}")

    print("""
    CONCLUSION
      Embed only what is small, bounded and always read with its parent.
      10,000 comments are none of those things, so comments move out into
      their own collection (referenced), and buckets of ~100 are used when
      read locality matters. A tiny preview array can stay in the post.
      MongoDB itself follows this rule: GridFS stores the mini video as
      many 255 KB chunk documents instead of one giant document.""")

    print("\n--- Step 8: export ---")
    export_json(db["viral_post"], "viral_post.json")
    export_json(buckets, "comment_buckets_sample.json", limit=3,
                note="(first 3 buckets only - 101 buckets exist)")
    export_json(db["viral_comments"], "viral_comments_sample.json", limit=20,
                note="(first 20 of 10,000 referenced comments)")

    banner("LAB 3.2 TRY IT YOURSELF COMPLETE")


if __name__ == "__main__":
    main()
