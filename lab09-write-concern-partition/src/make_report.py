"""Build the submission PDF from the REAL results saved by Lab 9.1 and Lab 9.2."""
import argparse
import html
import os
import re

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from common import RESULTS_DIR, load_json

SS = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=SS["BodyText"], fontSize=9.5, leading=13)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.8, leading=10)
CODE = ParagraphStyle("code", parent=BODY, fontName="Courier", fontSize=8.2, leading=10.5,
                      backColor=colors.HexColor("#F2F4F7"), borderPadding=4, leftIndent=4)
H1 = ParagraphStyle("h1", parent=SS["Heading1"], fontSize=16, spaceAfter=6, textColor=colors.HexColor("#14365D"))
H2 = ParagraphStyle("h2", parent=SS["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#14365D"))
H3 = ParagraphStyle("h3", parent=SS["Heading3"], fontSize=10.5, spaceBefore=6, spaceAfter=2)
TITLE = ParagraphStyle("title", parent=SS["Title"], fontSize=21, textColor=colors.HexColor("#14365D"))


def P(text, style=BODY):
    return Paragraph(text, style)


def esc(s):
    return html.escape(str(s))


def table(rows, widths, header=True, font=8.5, zebra=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    st = [("FONTSIZE", (0, 0), (-1, -1), font), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C0CC")),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14365D")),
               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F5F7FA")))
    t.setStyle(TableStyle(st))
    return t


def bar_chart(results):
    short = []
    for r in results:
        w = {"1": "w1", "majority": "wMaj"}.get(str(r["w"]), "w" + str(r["w"]))
        short.append(f"{w} j{'1' if r['j'] else '0'}")
    d = Drawing(480, 210)
    d.add(String(240, 196, "Average latency per write (ms)", textAnchor="middle", fontSize=10, fontName="Helvetica-Bold"))
    ch = VerticalBarChart()
    ch.x, ch.y, ch.width, ch.height = 45, 38, 415, 140
    ch.data = [[round(r["avg_ms"], 2) for r in results]]
    ch.categoryAxis.categoryNames = short
    ch.categoryAxis.labels.fontSize = 8
    ch.valueAxis.valueMin = 0
    ch.valueAxis.labels.fontSize = 8
    ch.bars[0].fillColor = colors.HexColor("#2F6DB5")
    ch.barLabelFormat = "%0.2f"
    ch.barLabels.fontSize = 7.5
    ch.barLabels.nudge = 7
    d.add(ch)
    return d


def analysis_71(results):
    by = {r["label"]: r for r in results}
    labels = [r["label"] for r in results]
    w1, w1j = by[labels[0]], by[labels[1]]
    wm, wmj = by[labels[2]], by[labels[3]]
    wa, waj = by[labels[4]], by[labels[5]]
    ranking = sorted(results, key=lambda r: r["avg_ms"])
    out = []
    out.append(P("<b>Measured ranking (fastest to slowest, by average latency):</b> " +
                 " &lt; ".join(f"{esc(r['label'])} ({r['avg_ms']:.2f} ms)" for r in ranking) + ".", BODY))
    out.append(P(f"<b>Cost of replication.</b> Relative to w:1 (j:false, {w1['avg_ms']:.2f} ms), "
                 f"w:majority is <b>{wm['avg_ms'] / w1['avg_ms']:.1f}x</b> and w:all (w:3) is "
                 f"<b>{wa['avg_ms'] / w1['avg_ms']:.1f}x</b> slower on average.", BODY))
    rows = [["Pair", "j:false (ms)", "j:true (ms)", "Change"]]
    for name, a, b in (("w:1", w1, w1j), ("w:majority", wm, wmj), ("w:all (w:3)", wa, waj)):
        rows.append([name, f"{a['avg_ms']:.2f}", f"{b['avg_ms']:.2f}", f"{(b['avg_ms'] - a['avg_ms']) / a['avg_ms'] * 100:+.0f}%"])
    out += [Spacer(1, 3), P("<b>Activity 9.1 - effect of journaling (j:true vs j:false):</b>", BODY),
            table(rows, [40 * mm, 35 * mm, 35 * mm, 30 * mm])]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lab report")
    ap.add_argument("--docker-url", required=True, help="https://hub.docker.com/r/<user>/<repo>")
    ap.add_argument("--name", default="")
    ap.add_argument("--student-id", default="")
    ap.add_argument("--course", default="NoSQL Databases using MongoDB")
    ap.add_argument("--out", default=os.path.join(RESULTS_DIR, "Lab09_Report.pdf"))
    a = ap.parse_args(argv)

    r1 = load_json("lab_01_results.json")
    r2 = load_json("lab_02_results.json")
    res = r1["results"]

    m = re.search(r"hub\.docker\.com/r/([^/\s]+/[^/\s]+)", a.docker_url)
    image = (m.group(1) + ":latest") if m else "<dockerhub-user>/nosql-lab09:latest"

    doc = SimpleDocTemplate(a.out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Lab 09 - Write Concern Latency and Network Partition", author=a.name or "Student")
    S = []

    # ---------------- cover
    S += [Spacer(1, 10 * mm), P("Lab 09 Report", TITLE),
          P("Write Concern Latency &amp; Network Partition Simulation", ParagraphStyle("st", parent=BODY, fontSize=13, alignment=1)),
          Spacer(1, 6 * mm)]
    info = [["Course", esc(a.course)], ["Student", esc(a.name) or "-"], ["Student ID", esc(a.student_id) or "-"],
            ["Technology", "MongoDB 7 replica set (3 data-bearing members), PyMongo, Docker"],
            ["Results measured", esc(r1["measured_at"])]]
    S.append(table([[P(f"<b>{k}</b>", BODY), P(v, BODY)] for k, v in info], [38 * mm, 130 * mm], header=False, zebra=False))
    S += [Spacer(1, 6 * mm), P("Docker Hub URL (image used for the demonstration)", H3),
          P(f'<a href="{esc(a.docker_url)}" color="blue"><u>{esc(a.docker_url)}</u></a>', ParagraphStyle("u", parent=BODY, fontSize=12)),
          Spacer(1, 2 * mm), P(f"Image: <font face='Courier'>{esc(image)}</font>", BODY)]

    S.append(P("How to run the demonstration (exactly what the grader needs)", H2))
    S.append(P("Requires only Docker Desktop. Commands are identical on Windows, macOS and Linux:", BODY))
    cmds = [f"docker pull {image}",
            f"docker run --rm {image} print-compose > docker-compose.yml",
            "docker compose up -d mongo1 mongo2 mongo3",
            "docker compose run --rm lab setup      # initiates replica set rs0",
            "docker compose run --rm lab lab01      # Lab 9.1 + j:true/j:false activity",
            "docker compose run --rm lab lab02      # Lab 9.2 network partition",
            "docker compose down -v                 # clean up"]
    S.append(Preformatted("\n".join(cmds), ParagraphStyle("pre", parent=CODE, backColor=colors.HexColor("#F2F4F7"))))
    S.append(PageBreak())

    # ---------------- Lab 9.1
    S += [P("Lab 9.1 - Measure Write Concern Latency", H1),
          P("<b>Objective.</b> Measure the impact of different write concerns on write latency.", BODY),
          P("<b>Method.</b> A Python/PyMongo script (<font face='Courier'>lab_01_write_concern_latency.py</font>) connects to the "
            "3-member replica set and inserts "
            f"<b>{r1['doc_count']:,}</b> small documents one at a time (sequential, acknowledged inserts) for each write-concern "
            "configuration. Each configuration uses a fresh collection and a 50-write warm-up that is excluded from the "
            "measurement. Total time is measured around the whole loop; per-write latency is measured around every "
            "<font face='Courier'>insert_one</font> call with <font face='Courier'>time.perf_counter()</font>. "
            "The write concern is attached to the collection handle (<font face='Courier'>get_collection(..., write_concern=WriteConcern(w, j))</font>).", BODY),
          P("<b>Note on w:all.</b> MongoDB has no literal <i>w:\"all\"</i> option. Acknowledgement from every member is requested "
            "by giving <i>w</i> the number of data-bearing members; with 3 members <b>w:all = w:3</b>.", BODY),
          P("1. Results table", H2)]
    rows = [["Configuration", "Total time for 1,000 writes (s)", "Avg latency / write (ms)", "P50 (ms)", "P99 (ms)", "Throughput (writes/s)", "vs w:1,j:false"]]
    for r in res:
        rows.append([esc(r["label"]), f"{r['total_s']:.2f}", f"{r['avg_ms']:.2f}", f"{r['p50_ms']:.2f}",
                     f"{r['p99_ms']:.2f}", f"{r['ops_per_s']:.0f}", f"{r['avg_ms'] / res[0]['avg_ms']:.2f}x"])
    rows[0] = [P(f"<b>{h}</b>", ParagraphStyle("th", parent=SMALL, textColor=colors.white)) for h in rows[0]]
    S.append(table(rows, [34 * mm, 28 * mm, 24 * mm, 17 * mm, 17 * mm, 25 * mm, 23 * mm], font=8.3))
    S += [Spacer(1, 2 * mm), P("Average latency per write = total time / 1,000. P50/P99 are the median and 99th-percentile "
                               "single-write latency.", SMALL), Spacer(1, 3 * mm), bar_chart(res),
          P("Chart key: w1 = w:1, wMaj = w:majority, w3 = w:all (w:3); j0 = j:false, j1 = j:true.", SMALL)]

    tr = os.path.join(RESULTS_DIR, "Write-Concern-TradeOffs.jpg")
    if os.path.exists(tr):
        S += [Spacer(1, 3 * mm), Image(tr, width=150 * mm, height=95 * mm, kind="proportional")]

    S.append(P("2. Analysis of the differences", H2))
    S += analysis_71(res)
    S.append(P("Why the numbers differ", H3))
    for t in [
        "<b>w:1</b> - the primary acknowledges as soon as the write is applied in its own memory. No network round-trip to any other member is needed, so this is the fastest option. The price: if the primary fails before secondaries copy the write, it can be rolled back.",
        "<b>w:majority</b> - for a 3-member set the primary must wait until at least one secondary has fetched the write from the oplog and applied it. This adds at least one replication round-trip to every write, which is why it is slower than w:1. The benefit: a majority-acknowledged write cannot be rolled back after a failover.",
        "<b>w:all (w:3)</b> - the primary waits for both secondaries, so latency is set by the slowest member. It gives the strongest guarantee but is the least available: if any one member is down, such writes cannot be acknowledged and will time out.",
        "<b>j:true</b> - an independent setting. It makes the member that acknowledges wait until the write is flushed to the on-disk journal, so it survives a crash of that machine. It adds disk-flush latency on top of whatever replication wait the 'w' value imposes.",
    ]:
        S.append(P("&bull; " + t, BODY))
    S.append(P("Interpretation of this run", H3))
    S.append(P("All three members run as containers on one machine, so the network round-trip is very small compared with a real "
               "multi-server or multi-region deployment; the slowdown seen here is mainly replication processing (oplog fetch + apply + "
               "progress report) and the journal flush. Over a real network the w:majority / w:all penalty would be larger (the theory "
               "figure of roughly 2-5x depends on network conditions). Absolute values vary between runs and machines; the ordering "
               "and the trend are what matter.", BODY))
    S.append(PageBreak())

    # ---------------- Lab 9.2
    S += [P("Lab 9.2 - Simulate a Network Partition", H1),
          P("<b>Objective.</b> Isolate members of the replica set using Docker network manipulation, observe the replica-set state, "
            "test w:1 and w:majority writes during the partition, then heal it and observe recovery.", BODY),
          P("<b>Method.</b> <font face='Courier'>lab_02_simulate_partition.py</font> runs the 3-node set from Chapter 8 "
            "(all members data-bearing, equal priority). An observer thread polls every node each second (the Lab 8.2 failover-observer "
            "idea) and logs every state change. Partitions are created with <font face='Courier'>docker network disconnect</font> and "
            "healed with <font face='Courier'>docker network connect</font>. Write operations use a 5 s wtimeout so that an impossible "
            "w:majority write returns a timeout instead of hanging.", BODY),
          P("Scenario summary", H2)]
    ssum = [["Item", "Observed"],
            ["Initial primary", esc(r2["initial_primary"])],
            ["Secondary isolated first / second", f"{esc(r2['isolated_first'])} / {esc(r2['isolated_second'])}"],
            ["Primary stepped down", (f"T+{r2['t_stepdown']}s - {r2['stepdown_after_s']}s after majority was lost") if r2["t_stepdown"] else "not observed"],
            ["New primary after healing", f"{esc(r2['new_primary'])} (elected {r2['election_after_heal_s']}s after reconnect)" if r2["new_primary"] else "none within 150s"],
            ["Did the former primary regain the role?", {True: "Yes", False: "No", None: "n/a"}[r2["former_primary_regained_role"]]],
            ["Former primary rejoined (saw a primary)", f"{r2['former_primary_rejoined_after_heal_s']}s after reconnect" if r2["former_primary_rejoined_after_heal_s"] is not None else "n/a"],
            ["All members caught up", f"{r2['caught_up_after_heal_s']}s after reconnect" if r2["caught_up_after_heal_s"] is not None else "not within 90s"],
            ["Documents per node after recovery", ", ".join(f"{k}={v}" for k, v in r2["docs_per_node"].items())]]
    hdr = ParagraphStyle("th2", parent=SMALL, textColor=colors.white)
    ssum = [[P(f"<b>{c}</b>", hdr) for c in ssum[0]]] + [[P(c, SMALL) for c in row] for row in ssum[1:]]
    S.append(table(ssum, [60 * mm, 112 * mm]))

    S.append(P("Write results at each stage", H2))
    ops = [["T+ (s)", "Stage", "Write concern", "Tag", "Outcome", "ms"]]
    for o in r2["operations"]:
        ops.append([P(str(o["t"]), SMALL), P(esc(o["phase"]), SMALL), P(esc(o["write_concern"]), SMALL),
                    P(esc(o["tag"]), SMALL), P(f"<b>{esc(o['outcome'])}</b>" + (f"<br/>{esc(o['detail'])}" if o["detail"] else ""), SMALL),
                    P(f"{o['ms']:.0f}", SMALL)])
    ops[0] = [P(f"<b>{h}</b>", ParagraphStyle('th3', parent=SMALL, textColor=colors.white)) for h in ops[0]]
    S.append(table(ops, [14 * mm, 30 * mm, 21 * mm, 46 * mm, 50 * mm, 11 * mm], font=7.8))

    S.append(P("Survival of writes made while no majority existed", H3))
    for tag, ok in r2["writes_survived"].items():
        verdict = {True: "survived (it was replicated to a majority after healing)",
                   False: "was ROLLED BACK (lost) - a different member became primary without it",
                   None: "could not be checked"}[ok]
        S.append(P(f"&bull; <font face='Courier'>{esc(tag)}</font>: {verdict}", BODY))

    S.append(PageBreak())
    S.append(P("Timeline of events (exact moments)", H2))
    tl = [[P("<b>T+ (s)</b>", ParagraphStyle('th4', parent=SMALL, textColor=colors.white)),
           P("<b>Clock</b>", ParagraphStyle('th5', parent=SMALL, textColor=colors.white)),
           P("<b>Event</b>", ParagraphStyle('th6', parent=SMALL, textColor=colors.white))]]
    for e in r2["events"]:
        txt = esc(e["event"])
        if e["kind"] in ("stepdown", "election", "partition", "stage"):
            txt = f"<b>{txt}</b>"
        tl.append([P(f"{e['t']:.1f}", SMALL), P(esc(e["clock"]), SMALL), P(txt, SMALL)])
    S.append(table(tl, [16 * mm, 18 * mm, 138 * mm], font=7.5))

    S.append(P("Explanation of the observed behaviour", H2))
    for t in [
        "<b>One secondary down:</b> the primary plus the remaining secondary are 2 of 3 voting members - a majority. No election is triggered, the primary keeps its role, and both w:1 and w:majority writes succeed. The isolated secondary is shown by rs.status() as not reachable/healthy (health 0) - it does not silently vanish - while its own view shows itself as SECONDARY with no primary.",
        "<b>Both secondaries down:</b> the primary can see only 1 of 3 voters. A w:majority write can never be acknowledged, so it ends with a write-concern timeout (the document was applied only on the primary and is not safe). Shortly afterwards (about the 10 s election timeout) the primary steps down because it cannot see a majority; with no primary the set is read-only: reads still work, writes are rejected (not primary / no primary available).",
        "<b>CAP trade-off:</b> w:1 keeps accepting writes locally while partitioned (availability) but those writes may be lost; w:majority refuses to claim success without a majority (consistency) and so becomes unavailable for writes. This is the Chapter 9 CAP theorem trade-off shown in practice.",
        "<b>Healing:</b> when connectivity returns, members hold an election; which member becomes primary depends on priority (all are equal here), oplog freshness and timing, so the former primary may or may not regain the role. Any member that had writes the new primary lacks rolls them back; the survival table above shows what happened to the writes made without a majority in this run. Finally every member catches up through oplog replication and all nodes hold the same documents.",
    ]:
        S.append(P("&bull; " + t, BODY))

    S.append(P("Conclusion", H2))
    S.append(P("Stronger write concerns (majority, all) and journal acknowledgement (j:true) cost latency but protect against data loss; "
               "w:1 is fastest and stays available during a partition but gives no durability guarantee. A replica set tolerates the loss of a "
               "minority of members transparently, but once the majority is lost the set stops accepting writes until the partition heals.", BODY))
    doc.build(S)
    print(f"[OK] PDF written to {a.out}")


if __name__ == "__main__":
    main()
