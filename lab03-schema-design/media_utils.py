"""
Shared helper used by all 4 lab scripts to store the photo as PIXEL DATA
(with an auto-generated description) and the mini video in GridFS.

Photo -> stored as raw pixel bytes (NumPy array) + width/height/channels +
         a text description (size, average color, brightness).
Video -> stored in GridFS (too large/binary to reasonably store as pixels
         frame-by-frame for this lab; referenced by ObjectId instead).
"""

from pathlib import Path

import numpy as np
from PIL import Image
from bson import Binary
import gridfs

MEDIA_DIR = Path(__file__).resolve().parent / "media"
PHOTO_FILE = MEDIA_DIR / "photo.jpg"
VIDEO_FILE = MEDIA_DIR / "minivideo.mp4"


def describe_image(pixels: np.ndarray, filename: str) -> str:
    """Build a short human-readable description from the pixel data itself."""
    h, w, c = pixels.shape
    avg = pixels.reshape(-1, c).mean(axis=0)
    brightness = float(pixels.mean())
    r, g, b = avg[0], avg[1], avg[2]
    dominant = "red" if r >= g and r >= b else ("green" if g >= r and g >= b else "blue")
    tone = "dark" if brightness < 85 else ("bright" if brightness > 170 else "medium-toned")
    return (
        f"{filename}: {w}x{h} pixels, {c} color channels (RGB). "
        f"Average color RGB=({r:.0f},{g:.0f},{b:.0f}), "
        f"average brightness={brightness:.1f}/255 ({tone}), "
        f"dominant channel: {dominant}."
    )


def build_photo_fields(prefix: str = "photo") -> dict:
    """
    Read media/photo.jpg, convert it to a pixel array, and return a dict of
    MongoDB fields: <prefix>_width, <prefix>_height, <prefix>_channels,
    <prefix>_pixels (raw pixel bytes as BSON Binary), <prefix>_description.
    Returns {} if the photo file is missing.
    """
    if not PHOTO_FILE.exists():
        print(f"[WARN] Photo not found at {PHOTO_FILE} - skipping photo fields")
        return {}

    img = Image.open(PHOTO_FILE).convert("RGB")
    pixels = np.array(img)  # (height, width, 3)
    description = describe_image(pixels, PHOTO_FILE.name)

    print(f"[OK] Photo converted to pixel array: shape={pixels.shape}")
    print(f"     Description: {description}")

    return {
        f"{prefix}_width": int(pixels.shape[1]),
        f"{prefix}_height": int(pixels.shape[0]),
        f"{prefix}_channels": int(pixels.shape[2]),
        f"{prefix}_pixels": Binary(pixels.tobytes()),
        f"{prefix}_description": description,
    }


def rebuild_image_from_fields(doc: dict, prefix: str = "photo") -> np.ndarray:
    """Reverse of build_photo_fields: turn stored pixel bytes back into an array."""
    w = doc[f"{prefix}_width"]
    h = doc[f"{prefix}_height"]
    c = doc[f"{prefix}_channels"]
    flat = np.frombuffer(doc[f"{prefix}_pixels"], dtype=np.uint8)
    return flat.reshape((h, w, c))


def store_video_gridfs(db, bucket_name: str = "fs") -> "ObjectId | None":
    """Store media/minivideo.mp4 in GridFS and return its file _id (or None)."""
    if not VIDEO_FILE.exists():
        print(f"[WARN] Video not found at {VIDEO_FILE} - skipping video upload")
        return None
    fs = gridfs.GridFS(db, collection=bucket_name)
    for old in fs.find({"filename": VIDEO_FILE.name}):
        fs.delete(old._id)
    video_id = fs.put(
        VIDEO_FILE.read_bytes(),
        filename=VIDEO_FILE.name,
        contentType="video/mp4",
    )
    print(f"[OK] Mini video stored in GridFS bucket '{bucket_name}' -> _id {video_id}")
    return video_id
