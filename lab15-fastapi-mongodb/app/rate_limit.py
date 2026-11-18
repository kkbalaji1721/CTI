"""
Rate limiting with MongoDB as the counter store (Lab 15.1, task 3).

Algorithm: fixed-window counter.
  * one document per (scope, time-bucket) in the `rate_limits` collection
  * every request does ONE atomic find_one_and_update (MongoDB findAndModify) with $inc + upsert,
    so concurrent requests can never lose an increment
  * the TTL index on `timestamp` removes old buckets automatically
"""
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Response
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from . import config
from .db import get_db


def _hit(scope: str, bucket: int, window: int) -> int:
    key = f"{scope}:{bucket}"
    update = {
        "$inc": {"count": 1},
        "$setOnInsert": {
            "scope": scope,
            "timestamp": datetime.fromtimestamp(bucket * window, tz=timezone.utc),
        },
    }
    doc = get_db().rate_limits.find_one_and_update(
        {"_id": key}, update, upsert=True, return_document=ReturnDocument.AFTER
    )
    return doc["count"]


def check_rate_limit(scope: str, response: Response, limit: Optional[int] = None) -> None:
    limit = limit if limit is not None else config.RATE_LIMIT_MAX
    window = config.RATE_LIMIT_WINDOW
    now = time.time()
    bucket = int(now // window)
    try:
        count = _hit(scope, bucket, window)
    except DuplicateKeyError:  # two first-requests raced on the upsert -> retry once
        count = _hit(scope, bucket, window)

    reset_in = int((bucket + 1) * window - now) + 1
    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(0, limit - count)),
        "X-RateLimit-Reset": str(reset_in),
    }
    if count > limit:
        headers["Retry-After"] = str(reset_in)
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.", headers=headers)
    for k, v in headers.items():
        response.headers[k] = v
