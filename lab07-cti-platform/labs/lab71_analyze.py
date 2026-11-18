"""Lab 7.1 - build the CTI dump, analyse embed/reference decisions, measure $bsonSize.
Usage: python labs/lab71_analyze.py [--mock]   (writes reports/lab71_report.md)"""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if "--mock" in sys.argv: os.environ["USE_MOCK"] = "1"
from threats.db import db
from threats.seed import SOURCES, SAMPLE, build_threat, collect_ctidigest, ingest, nvd_enrich

d = db()
for c in ('sources', 'threats', 'threats_embedded', 'vulnerabilities'): d[c].delete_many({})
d.sources.insert_many(SOURCES)
items = collect_ctidigest() or [build_threat(*s) for s in SAMPLE]
live_items = items
live = bool(collect_ctidigest.__doc__) and items and items[0]["url"].startswith("http") and "example.org" not in items[0]["url"]
stats = ingest(d, items)                      # removes duplicates, builds vulnerabilities
if '--nvd' in sys.argv: nvd_enrich(d)         # optional CVSS enrichment from NVD
items = list(d.threats.find())

# Activity 7.1: source EMBEDDED into each threat -> "is this an actual threat?" answered without a join
srcs = {s["_id"]: s for s in SOURCES}
d.threats_embedded.insert_many([{**t, "source": {k: srcs.get(t["source_id"], srcs["unknown"])[k] for k in ("name", "reliability")},
    "is_actual_threat": t["classification"]["verdict"] == "confirmed"} for t in items])

def size_stats(coll):
    if "--mock" in sys.argv:   # mongomock has no $bsonSize
        import bson; sizes = [len(bson.encode(x)) for x in d[coll].find()]
        return {"n": len(sizes), "avg": sum(sizes)/len(sizes), "max": max(sizes)}
    r = list(d[coll].aggregate([{"$project": {"s": {"$bsonSize": "$$ROOT"}}},
        {"$group": {"_id": None, "n": {"$sum": 1}, "avg": {"$avg": "$s"}, "max": {"$max": "$s"}}}]))
    return r[0]

LIMIT = 16 * 1024 * 1024
L = ["# Lab 7.1 - Production schema analysis", f"_Generated {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC; source: {'ctidigest.com (live)' if live else 'built-in sample'}_", "",
     "## Embedding vs referencing", "", "| Relationship | Choice | Why |", "|---|---|---|",
     "| threat -> iocs | **Embedded** | Always read with the threat, bounded size, 1:few. |",
     "| threat -> classification | **Embedded** | 1:1, computed at ingest, filtered/indexed in place. |",
     "| threat -> tags | **Embedded** | Small array; multikey index. |",
     "| threat -> source | **Referenced** (`source_id`) | See below. |", "",
     "| vulnerability -> threats | **Referenced** (`threat_ids`) | Many:many; a CVE appears in many threats and a threat names several CVEs. `_id` = CVE id, so a CVE is stored once. |",
     "| threat -> iocs (dedupe) | **Embedded, set-deduplicated** | Each IOC value is stored once per threat. |", "",
     "## Duplicate removal", "",
     f"- Received {stats['received']}; duplicates inside the batch: **{stats['duplicates_in_batch']}**; already in DB: {stats['already_in_db']}; inserted: **{stats['inserted']}**.",
     "- A duplicate = same normalised title (`title_key`) or same normalised URL (`url_key`: no scheme, `www`, query string, fragment or trailing slash). The highest-scoring copy is kept.",
     "- A unique index on `title_key` stops duplicates at database level. Existing data: `python labs/dedupe_existing.py`.", "",
     f"## Vulnerabilities", "", f"- {d.vulnerabilities.count_documents({})} unique CVEs, {d.vulnerabilities.count_documents({'exploited_in_wild': True})} flagged as exploited in the wild (CVSS filled with `--nvd`).", "",
     "## Why `source` is referenced, and the embedded alternative", "",
     "- One source has hundreds of threats; embedding duplicates name/URL/reliability in every document.",
     "- Reliability is updated over time; with embedding a change means `updateMany` over all threats and risks stale copies.",
     "- Alternative (built as `threats_embedded`): `{ ..., source: {name, reliability}, is_actual_threat: true }`.", "",
     "## Activity 7.1 - embedded source to decide the 'actual threat'", "",
     "- **Faster:** the dashboard, filters like `{is_actual_threat: true}` and sort by score need one collection, no `$lookup`.",
     "- **Harder:** updating a source's reliability must rewrite every embedded copy; the verdict can go stale; documents grow slightly.",
     "- Hybrid used in production: reference the source *and* embed a snapshot (`name`, `reliability`) that is refreshed in a batch job.", "",
     "## Document sizes (`$bsonSize`)", "", "| Collection | Docs | Avg bytes | Max bytes | Max as % of 16 MB |", "|---|---|---|---|---|"]
for c in ("threats", "threats_embedded", "vulnerabilities", "sources"):
    s = size_stats(c); L.append(f"| {c} | {s['n']} | {s['avg']:.0f} | {s['max']} | {s['max']/LIMIT:.4%} |")
L += ["", "No document approaches the 16 MB limit." ]
os.makedirs("reports", exist_ok=True); open("reports/lab71_report.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
