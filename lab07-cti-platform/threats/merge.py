"""Vulnerability import (CISA KEV) + duplicate removal + fragment merging (kotha / kuruva / rajesh -> 'kotha kuruva rajesh')."""
import csv, json
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
SAMPLE_KEV = [  # offline fallback (note the repeated CVE: it must be stored once)
 {"cveID": "CVE-2024-3400", "vendorProject": "Palo Alto Networks", "product": "PAN-OS", "vulnerabilityName": "PAN-OS Command Injection", "dateAdded": "2024-04-12"},
 {"cveID": "CVE-2023-4863", "vendorProject": "Google", "product": "Chromium WebP", "vulnerabilityName": "WebP Heap Buffer Overflow", "dateAdded": "2023-09-13"},
 {"cveID": "CVE-2024-3400", "vendorProject": "Palo Alto Networks", "product": "PAN-OS", "vulnerabilityName": "PAN-OS Command Injection", "dateAdded": "2024-04-12"},
 {"cveID": "cve-2023-4863", "vendorProject": "Google", "product": "Chromium WebP", "vulnerabilityName": "WebP Heap Buffer Overflow", "dateAdded": "2023-09-13"},
]
DEMO_FRAGMENTS = [("R1", 1, "kotha"), ("R1", 2, "kuruva"), ("R1", 3, "rajesh"), ("R1", 4, "Rajesh"),
                  ("R2", 1, "asha"), ("R2", 2, "Rao"), ("R2", 3, "asha")]

def merge_name(parts):
    """Split every fragment into words, drop repeated words (case-insensitive), keep first-seen order."""
    seen, out = set(), []
    for p in parts:
        for w in str(p).split():
            if w.lower() not in seen: seen.add(w.lower()); out.append(w)
    return " ".join(out)

def fetch_kev(path=None):
    if path: return json.load(open(path))["vulnerabilities"], f"file {path}"
    try:
        import requests
        return requests.get(KEV_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).json()["vulnerabilities"], "CISA KEV (live)"
    except Exception:
        return SAMPLE_KEV, "built-in sample (CISA KEV not reachable)"

def import_kev(db, path=None):
    """raw_records (untouched copy) -> kev_clean (unique per CVE) -> vulnerabilities (shown on the website)."""
    rows, origin = fetch_kev(path)
    for c in ("raw_records", "kev_clean"): db[c].delete_many({})
    db.raw_records.insert_many([dict(r) for r in rows])
    for r in rows:
        r = {k: v for k, v in r.items() if k != "_id"}; cid = r["cveID"].strip().upper(); r["cveID"] = cid
        db.kev_clean.update_one({"_id": cid}, {"$setOnInsert": r}, upsert=True)      # _id = CVE id => no duplicates
    for v in db.kev_clean.find():
        db.vulnerabilities.update_one({"_id": v["_id"]}, {"$set": {"cvss": None, "cvss_severity": None, "exploited_in_wild": True,
            "description": f"{v.get('vulnerabilityName','')} ({v.get('vendorProject','')} {v.get('product','')})".strip(),
            "date_added": v.get("dateAdded")}, "$setOnInsert": {"threat_ids": []}}, upsert=True)
    return {"origin": origin, "raw": len(rows), "unique": db.kev_clean.count_documents({}), "duplicates_removed": len(rows) - db.kev_clean.count_documents({})}

def load_fragments(db, csv_path=None):
    """Fragments come from a CSV (record_id,seq,name) or the built-in demo."""
    db.fragments.delete_many({})
    rows = [(r["record_id"], int(r["seq"]), r["name"]) for r in csv.DictReader(open(csv_path))] if csv_path else DEMO_FRAGMENTS
    db.fragments.insert_many([{"record_id": a, "seq": b, "name": c} for a, b, c in rows])

def merge_fragments(db):
    db.merged.delete_many({})
    for g in db.fragments.aggregate([{"$sort": {"record_id": 1, "seq": 1}}, {"$group": {"_id": "$record_id", "parts": {"$push": "$name"}}}]):
        db.merged.insert_one({"_id": g["_id"], "name": merge_name(g["parts"]), "fragments": len(g["parts"])})
    return db.merged.count_documents({})

def merged_md(db):
    L = ["# Merged records", "", "| Record | Fragments | Merged name |", "|---|---|---|"]
    L += [f"| {m['_id']} | {m['fragments']} | **{m['name']}** |" for m in db.merged.find().sort("_id", 1)]
    return "\n".join(L) + "\n"
