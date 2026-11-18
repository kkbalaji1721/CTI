import re
from django.http import HttpResponse, Http404
from django.shortcuts import render
from .db import db
from .seed import detect_indicator
from .merge import merged_md
from .markdown import threat_md, report_md, vulns_md

def _ids(docs):
    docs = list(docs)
    for x in docs: x['id'] = x['_id']
    return docs

def _vulns(d, limit=200):
    vs = list(d.vulnerabilities.find())
    for v in vs: v["id"] = v["_id"]; v["n"] = len(v["threat_ids"])
    vs.sort(key=lambda v: (-(v["cvss"] or 0), not v["exploited_in_wild"], -v["n"], v["id"]))
    return vs[:limit]

def vulnerabilities(request):
    return render(request, "threats/vulns.html", {"vs": _vulns(db())})

def vuln_detail(request, cve):
    d = db(); v = d.vulnerabilities.find_one({"_id": cve.upper()})
    if not v: raise Http404
    v["cve"] = v["_id"]
    return render(request, "threats/vuln_detail.html", {"v": v, "ts": _ids(d.threats.find({"_id": {"$in": v["threat_ids"]}}))})

def download_vulns(request):
    return _md(vulns_md(_vulns(db())), "vulnerabilities.md")

def _md(text, name):
    r = HttpResponse(text, content_type="text/markdown; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{name}"'
    return r

def _query(request):
    q = request.GET.get("q", "").strip(); cat = request.GET.get("category", "")
    f = {}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        f["$or"] = [{"title": rx}, {"summary": rx}, {"tags": rx}, {"iocs.value": rx}, {"classification.category": rx}]
    if cat: f["classification.category"] = cat
    return q, cat, f

def dashboard(request):
    d = db()
    top = _ids(d.threats.find().sort("score", -1).limit(10))
    cats = [{"name": c["_id"], "n": c["n"]} for c in d.threats.aggregate([{"$group": {"_id": "$classification.category", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}])]
    ctx = {"vtop": _vulns(d, 5), "vtotal": d.vulnerabilities.count_documents({}), "top": top, "cats": cats, "total": d.threats.count_documents({}),
           "confirmed": d.threats.count_documents({"classification.verdict": "confirmed"})}
    return render(request, "threats/dashboard.html", ctx)

def search(request):
    q, cat, f = _query(request)
    d = db()
    res = _ids(d.threats.find(f).sort("score", -1).limit(100))
    cats = sorted(d.threats.distinct("classification.category"))
    ind = detect_indicator(q) if q else None
    vuln = d.vulnerabilities.find_one({"_id": q.upper()}) if ind == "cve" else None
    if vuln: vuln["cve"] = vuln["_id"]
    return render(request, "threats/search.html", {"vuln": vuln, "q": q, "cat": cat, "res": res, "cats": cats, "ind": ind})

def detail(request, tid):
    d = db(); t = d.threats.find_one({"_id": tid})
    if not t: raise Http404
    t["id"] = t["_id"]
    return render(request, "threats/detail.html", {"t": t, "src": d.sources.find_one({"_id": t["source_id"]})})

def download_top(request):
    return _md(report_md("Top Threats", list(db().threats.find().sort("score", -1).limit(10))), "top-threats.md")

def download_search(request):
    q, cat, f = _query(request)
    return _md(report_md(f"Search results: {q or 'all'}", list(db().threats.find(f).sort("score", -1).limit(100))), "search-results.md")

def download_threat(request, tid):
    d = db(); t = d.threats.find_one({"_id": tid})
    if not t: raise Http404
    return _md(threat_md(t, d.sources.find_one({"_id": t["source_id"]})), f"{tid}.md")

def merged(request):
    d = db()
    frags = {}
    for f in d.fragments.find().sort([("record_id", 1), ("seq", 1)]): frags.setdefault(f["record_id"], []).append(f["name"])
    rows = [{"id": m["_id"], "parts": frags.get(m["_id"], []), "name": m["name"]} for m in d.merged.find().sort("_id", 1)]
    return render(request, "threats/merged.html", {"rows": rows, "raw": d.raw_records.count_documents({}), "unique": d.kev_clean.count_documents({})})

def download_merged(request):
    return _md(merged_md(db()), "merged-records.md")
