import datetime as dt
def threat_md(t, src=None):
    c = t["classification"]
    L = [f"# {t['title']}", "", f"- **Category:** {c['category']} (confidence {c['confidence']:.0%})",
         f"- **Verdict:** {c['verdict']}", f"- **Score:** {t['score']}/100",
         f"- **Source:** {src['name'] if src else t['source_id']}" + (f" (reliability {src['reliability']})" if src else ""),
         f"- **Link:** {t.get('url') or 'n/a'}", "", "## Summary", "", t["summary"], "", "## Indicators of Compromise", ""]
    L += [f"- `{i['type']}`: `{i['value']}` — [VirusTotal](https://www.virustotal.com/gui/search/{i['value']})" for i in t["iocs"]] or ["_None extracted._"]
    return "\n".join(L) + "\n"
def report_md(title, threats):
    L = [f"# {title}", "", f"_Generated {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC — {len(threats)} threats_", "",
         "| # | Threat | Category | Verdict | Score |", "|---|---|---|---|---|"]
    for n, t in enumerate(threats, 1):
        L.append(f"| {n} | [{t['title']}]({t.get('url') or '#'}) | {t['classification']['category']} | {t['classification']['verdict']} | {t['score']} |")
    return "\n".join(L) + "\n"

def vulns_md(vulns):
    L = ["# Vulnerabilities", "", f"_{len(vulns)} unique CVEs_", "", "| CVE | CVSS | Exploited in wild | Threats | Links |", "|---|---|---|---|---|"]
    for v in vulns:
        L.append(f"| {v['_id']} | {v['cvss'] if v['cvss'] is not None else 'n/a'} | {'yes' if v['exploited_in_wild'] else 'no'} | {len(v['threat_ids'])} | "
                 f"[NVD](https://nvd.nist.gov/vuln/detail/{v['_id']}) / [VirusTotal](https://www.virustotal.com/gui/search/{v['_id']}) |")
    return "\n".join(L) + "\n"
