#!/usr/bin/env python3
"""Creates the submission PDF containing the Docker Hub URL.
Usage: python3 make_pdf.py https://hub.docker.com/r/<user>/mongodb-lab14 --name "Your Name" --out submission.pdf"""
import argparse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted

p = argparse.ArgumentParser()
p.add_argument("url")
p.add_argument("--name", default="")
p.add_argument("--out", default="submission.pdf")
a = p.parse_args()

repo = a.url.rstrip("/").split("/r/")[-1]
s = getSampleStyleSheet()
doc = SimpleDocTemplate(a.out, pagesize=A4)
story = [
    Paragraph("Chapter 14 - MongoDB Labs 14.1 and 14.2", s["Title"]),
    Paragraph(f"Student: {a.name}" if a.name else "", s["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>Docker Hub URL:</b>", s["Heading3"]),
    Paragraph(f'<a href="{a.url}" color="blue">{a.url}</a>', s["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>How to run the demonstration:</b>", s["Heading3"]),
    Preformatted(f"docker pull {repo}\ndocker run -it --rm {repo}", s["Code"]),
    Spacer(1, 12),
    Paragraph("<b>Contents:</b> Lab 14.1 monitor.py (metrics table, 30 s logging, WARNING alerts, webhook extension); "
              "Lab 14.2 backup_verify.py (timestamped mongodump, hourly schedule, 7-day retention, restore "
              "verification, 1k/10k/100k benchmark, RPO/RTO).", s["Normal"]),
]
doc.build(story)
print("Created", a.out)
