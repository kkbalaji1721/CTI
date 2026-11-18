"""Seed data, classifier and ctidigest.com collector (shared by Django + labs)."""
import re, datetime as dt

SOURCES = [
 {"_id": "thehackernews", "name": "The Hacker News", "url": "https://thehackernews.com", "reliability": 80},
 {"_id": "bleepingcomputer", "name": "BleepingComputer", "url": "https://www.bleepingcomputer.com", "reliability": 85},
 {"_id": "krebs", "name": "Krebs on Security", "url": "https://krebsonsecurity.com", "reliability": 90},
 {"_id": "cisa", "name": "CISA Advisories", "url": "https://www.cisa.gov", "reliability": 98},
 {"_id": "unknown", "name": "Unverified blog", "url": "", "reliability": 30},
]
RULES = [  # (category, keywords, base severity)
 ("Ransomware", ["ransomware", "lockbit", "encrypt", "extortion"], 90),
 ("APT / Nation-state", ["apt", "nation-state", "state-sponsored", "lazarus", "espionage"], 85),
 ("Vulnerability", ["cve-", "vulnerability", "zero-day", "rce", "exploit"], 75),
 ("Data Breach", ["breach", "leak", "exposed", "stolen data"], 70),
 ("Phishing", ["phishing", "credential", "spoof", "smishing"], 60),
 ("Malware", ["malware", "trojan", "stealer", "backdoor", "botnet", "loader"], 65),
 ("DDoS", ["ddos", "denial-of-service"], 50),
]
IOC_RE = {"ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "sha256": r"\b[a-fA-F0-9]{64}\b",
          "md5": r"\b[a-fA-F0-9]{32}\b", "cve": r"(?i)CVE-\d{4}-\d{4,7}"}

def classify(text):
    t = text.lower()
    for cat, kws, sev in RULES:
        hits = sum(k in t for k in kws)
        if hits:
            return {"category": cat, "confidence": min(0.5 + 0.15 * hits, 0.99), "severity": sev}
    return {"category": "General Intel", "confidence": 0.4, "severity": 30}

def extract_iocs(text):
    out = []
    for typ, rx in IOC_RE.items():
        vals = {v.upper() if typ == "cve" else v.lower() if typ in ("sha256", "md5") else v for v in re.findall(rx, text)}
        out += [{"type": typ, "value": v} for v in sorted(vals)]       # set() => duplicate IOCs removed
    return out

def detect_indicator(q):
    q = q.strip()
    for typ, rx in IOC_RE.items():
        if re.fullmatch(rx, q): return typ
    if re.match(r"https?://", q): return "url"
    if re.fullmatch(r"[\w.-]+\.[a-z]{2,}", q, re.I): return "domain"
    return None

def title_key(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()

def url_key(url):
    """Normalised URL: no scheme/www/query/fragment/trailing slash, so ?utm_x and http/https variants match."""
    if not url: return ""
    m = re.match(r"https?://(?:www\.)?([^/?#]+)([^?#]*)", url.lower())
    return (m.group(1) + m.group(2).rstrip("/")) if m else url.lower()

def build_threat(title, url, summary, source_id, published=None):
    srcs = {s["_id"]: s for s in SOURCES}
    c = classify(f"{title} {summary}")
    rel = srcs.get(source_id, srcs["unknown"])["reliability"]
    score = round(c["severity"] * 0.6 + rel * 0.4)          # ranking score
    uk, tk = url_key(url), title_key(title)
    return {"_id": re.sub(r"\W+", "-", tk).strip("-")[:80], "url_key": uk, "title_key": tk, "title": title.strip(), "url": url,
            "summary": summary, "published": published or dt.datetime.utcnow(),
            "source_id": source_id,                              # REFERENCE -> sources
            "classification": {"category": c["category"], "confidence": c["confidence"],
                               "verdict": "confirmed" if rel >= 70 and c["severity"] >= 50 else "unverified"},
            "score": score, "tags": [c["category"].lower().split()[0]],   # EMBEDDED
            "iocs": extract_iocs(f"{title} {summary}")}                    # EMBEDDED

SAMPLE = [
 ("LockBit affiliates hit hospitals with new ransomware build", "https://example.org/lockbit", "Extortion gang encrypt files; C2 at 185.220.101.4 and CVE-2024-3400 exploited.", "bleepingcomputer"),
 ("Lazarus APT targets crypto firms via backdoor", "https://example.org/lazarus", "State-sponsored espionage campaign delivers backdoor loader.", "thehackernews"),
 ("Zero-day RCE vulnerability CVE-2025-1234 exploited in the wild", "https://example.org/rce", "CISA adds exploit to KEV catalog; patch immediately.", "cisa"),
 ("Retailer confirms customer data breach", "https://example.org/breach", "Stolen data leak exposed 2M records.", "krebs"),
 ("Credential phishing kit spoofs Microsoft 365 login", "https://example.org/phish", "Phishing domain login-m365-secure.com harvests credentials.", "thehackernews"),
 ("New infostealer malware spreads via fake installers", "https://example.org/stealer", "Stealer trojan sha256 " + "a" * 64 + " observed.", "unknown"),
 ("Record DDoS attack peaks at 3 Tbps", "https://example.org/ddos", "Botnet-driven denial-of-service hits gaming provider.", "bleepingcomputer"),
 ("Critical Fortinet flaw CVE-2025-1234 under active attack", "https://example.org/forti", "Vulnerability exploited in the wild; also tracked as CVE-2025-1234 and CVE-2024-3400.", "thehackernews"),
 # --- deliberate duplicates (removed on ingest): same URL w/ tracking param, same title other source
 ("LockBit affiliates hit hospitals with new ransomware build", "https://www.example.org/lockbit/?utm_source=x", "Duplicate of first item.", "thehackernews"),
 ("Record  DDoS attack peaks at 3 Tbps!", "https://other.example.net/ddos-copy", "Duplicate title, different site.", "unknown"),
]

def seed(db):
    for c in ("sources", "threats", "vulnerabilities"): db[c].delete_many({})
    db.sources.insert_many(SOURCES)
    return ingest(db, [build_threat(*s) for s in SAMPLE])

def dedupe(items):
    """Keep the highest-scoring item per URL key or title key. Returns (unique, removed_count)."""
    kept, by_u, by_t = [], {}, {}
    for t in sorted(items, key=lambda x: -x["score"]):
        if (t["url_key"] and t["url_key"] in by_u) or t["title_key"] in by_t: continue
        kept.append(t); by_t[t["title_key"]] = 1
        if t["url_key"]: by_u[t["url_key"]] = 1
    return kept, len(items) - len(kept)

def ingest(db, items):
    """Dedupe within the batch AND against the DB, insert new threats, rebuild vulnerabilities."""
    uniq, dup_batch = dedupe(items); inserted = 0
    for t in uniq:
        ors = [{"title_key": t["title_key"]}] + ([{"url_key": t["url_key"]}] if t["url_key"] else [])
        if not db.threats.find_one({"$or": ors}):
            db.threats.insert_one(t); inserted += 1
    ensure_indexes(db); build_vulns(db)
    return {"received": len(items), "duplicates_in_batch": dup_batch,
            "already_in_db": len(uniq) - inserted, "inserted": inserted}

def remove_duplicates(db):
    """Clean an existing collection: keep best-scoring doc per title_key/url_key, delete the rest."""
    docs = list(db.threats.find())
    for t in docs:
        t.setdefault("title_key", title_key(t["title"])); t.setdefault("url_key", url_key(t.get("url", "")))
    kept, _ = dedupe(docs); keep = {t["_id"] for t in kept}
    gone = [t["_id"] for t in docs if t["_id"] not in keep]
    if gone: db.threats.delete_many({"_id": {"$in": gone}})
    for t in kept: db.threats.update_one({"_id": t["_id"]}, {"$set": {"title_key": t["title_key"], "url_key": t["url_key"]}})
    db.vulnerabilities.delete_many({}); build_vulns(db)
    return len(gone)

def build_vulns(db):
    """vulnerabilities: one doc per CVE (the _id => no duplicates); threats REFERENCED by id (many:many)."""
    for t in db.threats.find({"iocs.type": "cve"}):
        text = f"{t['title']} {t['summary']}".lower()
        for i in t["iocs"]:
            if i["type"] != "cve": continue
            db.vulnerabilities.update_one({"_id": i["value"].upper()}, {"$addToSet": {"threat_ids": t["_id"]},
                "$setOnInsert": {"cvss": None, "cvss_severity": None, "description": None, "exploited_in_wild": False}}, upsert=True)
            if any(k in text for k in ("in the wild", "actively", "under active", "kev", "exploited")):
                db.vulnerabilities.update_one({"_id": i["value"].upper()}, {"$set": {"exploited_in_wild": True}})

def nvd_enrich(db, limit=20):
    """Optional: fill CVSS/description from the NIST NVD API (rate-limited). Silent no-op when offline."""
    import time, requests
    for v in list(db.vulnerabilities.find({"cvss": None}).limit(limit)):
        try:
            j = requests.get("https://services.nvd.nist.gov/rest/json/cves/2.0", params={"cveId": v["_id"]}, timeout=15).json()["vulnerabilities"][0]["cve"]
            m = (j["metrics"].get("cvssMetricV31") or j["metrics"].get("cvssMetricV40") or [{}])[0].get("cvssData", {})
            db.vulnerabilities.update_one({"_id": v["_id"]}, {"$set": {"cvss": m.get("baseScore"), "cvss_severity": m.get("baseSeverity"),
                "description": next((d["value"] for d in j["descriptions"] if d["lang"] == "en"), None)}})
        except Exception: pass
        time.sleep(6.5)

def ensure_indexes(db):
    db.threats.create_index([("score", -1)])
    db.threats.create_index("classification.category")
    db.threats.create_index("iocs.value")
    db.threats.create_index("source_id")
    db.threats.create_index("title_key", unique=True, partialFilterExpression={"title_key": {"$exists": True}})  # DB-level duplicate guard

def collect_ctidigest(limit=40):
    """Scrape https://ctidigest.com/ headlines; returns [] on any network problem."""
    try:
        import requests
        html = requests.get("https://ctidigest.com/", timeout=15, headers={"User-Agent": "Mozilla/5.0"}).text
    except Exception:
        return []
    items, seen = [], set()
    for href, label in re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.S):
        title = re.sub(r"<[^>]+>|\s+", " ", label).strip()
        if len(title) < 25 or href in seen or "ctidigest.com" in href: continue
        seen.add(href)
        host = re.sub(r"^www\.", "", href.split("/")[2]).split(".")[0]
        sid = next((s["_id"] for s in SOURCES if s["_id"] in host), "unknown")
        items.append(build_threat(title, href, title, sid))
        if len(items) >= limit: break
    return items
