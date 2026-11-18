"""Professor's task: import vulnerability data, remove duplicates, merge fragments into one record.
Usage: python labs/lab_merge.py [--kev kev.json] [--fragments names.csv] [--mock]   -> reports/merge_report.md"""
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser(); ap.add_argument("--kev"); ap.add_argument("--fragments"); ap.add_argument("--mock", action="store_true"); a = ap.parse_args()
if a.mock: os.environ["USE_MOCK"] = "1"
from threats.db import db
from threats.merge import import_kev, load_fragments, merge_fragments, merged_md
d = db(); s = import_kev(d, a.kev); load_fragments(d, a.fragments); n = merge_fragments(d)
L = ["# Vulnerability import and merge report", "", f"- Source: {s['origin']}", f"- Raw records: {s['raw']}", f"- Unique CVEs kept: {s['unique']}",
     f"- Duplicates removed: {s['duplicates_removed']}", f"- Fragments: {d.fragments.count_documents({})} -> merged records: {n}", "", merged_md(d)]
os.makedirs("reports", exist_ok=True); open("reports/merge_report.md", "w").write("\n".join(L)); print("\n".join(L))
