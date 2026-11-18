# Threat Desk - Cyber Threat Intelligence platform (Django + MongoDB)

## Run (Linux/macOS; Windows works too, view in Microsoft Edge)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# with MongoDB running on localhost:27017
python labs/lab71_analyze.py          # builds data from ctidigest.com + Lab 7.1 report
python manage.py runserver            # http://127.0.0.1:8000
# no MongoDB? USE_MOCK=1 python manage.py runserver  (in-memory sample data)
```
## Features
- Dashboard: top 10 threats by score, category counts, download as Markdown.
- Search: keywords, IOCs, category filter; IP/domain/URL/hash/CVE queries get a VirusTotal lookup button; results downloadable as Markdown.
- Threat classification: rule-based category, confidence, severity, verdict (source reliability weighted).
- **Vulnerabilities:** one page per unique CVE (CVSS via `--nvd`, exploited-in-the-wild flag, linked threats), dashboard panel, `.md` download.
- **Duplicate removal:** normalised title/URL keys, unique index, `python labs/dedupe_existing.py` for existing data; IOCs deduplicated per threat.
- Per-threat Markdown download with VirusTotal links for each IOC.

## Professor's task: import, de-duplicate, merge
```bash
curl -o kev.json https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
python labs/lab_merge.py --kev kev.json --fragments names.csv   # names.csv: record_id,seq,name
```
See the **Merged records** page and `reports/merge_report.md`. Without `--fragments` the demo kotha / kuruva / rajesh is used.

## Labs
| Lab | File | Output |
|---|---|---|
| 7.1 + activity | `labs/lab71_analyze.py` | `reports/lab71_report.md` |
| 7.2 | `labs/lab72_workingset.py` | `reports/lab72_report.md` |
| 7.2 activity | `labs/lab72_monitor.py` | console, every 10 s |
