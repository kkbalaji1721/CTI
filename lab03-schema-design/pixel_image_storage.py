"""
Store an image in MongoDB as PIXEL DATA (not as one binary file).

Idea:
    - Read photo.jpg
    - Convert to a NumPy array of pixels (height x width x RGB)
    - Save width, height, mode, and the raw pixel bytes in MongoDB
    - Read it back and rebuild the image from those pixels

Run:  python pixel_image_storage.py
Needs: pip install pymongo pillow numpy
"""

import os
from pathlib import Path

import numpy as np
from PIL import Image
from pymongo import MongoClient
from bson import Binary

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "nosql_lab3"
PHOTO_FILE = Path(__file__).resolve().parent / "media" / "photo.jpg"


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    col = db["images_as_pixels"]

    # 1. Load the image and convert to a pixel array
    img = Image.open(PHOTO_FILE).convert("RGB")
    pixels = np.array(img)  # shape: (height, width, 3)
    print(f"[OK] Image loaded: {img.size}, pixel array shape = {pixels.shape}")

    # 2. Store width, height, and the raw pixel bytes in MongoDB
    doc = {
        "filename": PHOTO_FILE.name,
        "width": pixels.shape[1],
        "height": pixels.shape[0],
        "channels": pixels.shape[2],
        "mode": "RGB",
        "pixel_data": Binary(pixels.tobytes()),  # flattened pixel bytes
    }
    col.delete_many({"filename": PHOTO_FILE.name})
    result = col.insert_one(doc)
    print(f"[OK] Stored pixel data in MongoDB, _id = {result.inserted_id}")
    print(f"     pixel_data size = {len(doc['pixel_data'])} bytes "
          f"({pixels.shape[0]}x{pixels.shape[1]}x{pixels.shape[2]})")

    # 3. Read it back and rebuild the image from pixels
    saved = col.find_one({"filename": PHOTO_FILE.name})
    rebuilt = np.frombuffer(saved["pixel_data"], dtype=np.uint8)
    rebuilt = rebuilt.reshape((saved["height"], saved["width"], saved["channels"]))
    out_img = Image.fromarray(rebuilt, mode=saved["mode"])
    out_path = Path(__file__).resolve().parent / "media" / "rebuilt_from_pixels.jpg"
    out_img.save(out_path)
    print(f"[OK] Rebuilt image from pixel data -> {out_path.name}")

    # 4. Analyze the pixel data pulled from MongoDB
    print("\n--- Pixel Analysis (computed from data read out of MongoDB) ---")

    r, g, b = rebuilt[:, :, 0], rebuilt[:, :, 1], rebuilt[:, :, 2]
    avg_color = (float(r.mean()), float(g.mean()), float(b.mean()))
    print(f"Average color (R,G,B): "
          f"({avg_color[0]:.1f}, {avg_color[1]:.1f}, {avg_color[2]:.1f})")

    # brightness = average of all pixel channel values
    brightness = float(rebuilt.mean())
    print(f"Average brightness (0-255): {brightness:.1f}")

    # darkest / brightest pixel value
    print(f"Darkest pixel value : {int(rebuilt.min())}")
    print(f"Brightest pixel value: {int(rebuilt.max())}")

    # simple histogram: count pixels in 4 brightness bands
    gray = rebuilt.mean(axis=2)  # grayscale value per pixel
    bands = [(0, 64), (64, 128), (128, 192), (192, 256)]
    print("Brightness distribution:")
    for lo, hi in bands:
        count = int(((gray >= lo) & (gray < hi)).sum())
        pct = 100 * count / gray.size
        print(f"    {lo:3}-{hi:3}: {count:>7} pixels ({pct:5.1f}%)")

    # store the analysis results back in MongoDB, linked to the image
    analysis = {
        "avg_color_rgb": avg_color,
        "avg_brightness": brightness,
        "min_pixel": int(rebuilt.min()),
        "max_pixel": int(rebuilt.max()),
        "total_pixels": int(gray.size),
    }
    col.update_one({"_id": saved["_id"]}, {"$set": {"analysis": analysis}})
    print("\n[OK] Analysis results saved back into the same MongoDB document")


if __name__ == "__main__":
    main()
