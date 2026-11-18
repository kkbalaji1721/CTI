"""Remove duplicate threats already stored in MongoDB (keeps the highest-scoring copy), then rebuild vulnerabilities.
Usage: python labs/dedupe_existing.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from threats.db import db
from threats.seed import remove_duplicates, ensure_indexes
d = db(); n = remove_duplicates(d); ensure_indexes(d)
print(f"Removed {n} duplicate threat(s); {d.threats.count_documents({})} remain.")
