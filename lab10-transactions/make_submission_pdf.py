#!/usr/bin/env python3
"""Creates the PDF to submit.   Usage:
   pip install reportlab
   python make_submission_pdf.py --name "Your Name" --url https://hub.docker.com/r/USERNAME/mongodb-lab10 \
          --image USERNAME/mongodb-lab10:latest
"""
import argparse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

p = argparse.ArgumentParser()
p.add_argument("--name", required=True)
p.add_argument("--url", required=True, help="Docker Hub repository URL")
p.add_argument("--image", required=True, help="e.g. username/mongodb-lab10:latest")
p.add_argument("--out", default="Lab10_Submission.pdf")
a = p.parse_args()

s = getSampleStyleSheet()
doc = SimpleDocTemplate(a.out, pagesize=A4, title="Exercise-10 Submission")
mono = s["Code"]
story = [
    Paragraph("Exercise-10: Transactions, Atomicity, Durability &amp; Journaling", s["Title"]),
    Paragraph(f"<b>Student:</b> {a.name}", s["Normal"]), Spacer(1, 12),
    Paragraph("<b>Docker Hub URL:</b>", s["Normal"]),
    Paragraph(f'<link href="{a.url}" color="blue">{a.url}</link>', s["Normal"]), Spacer(1, 12),
    Paragraph("<b>Image:</b> " + a.image, s["Normal"]), Spacer(1, 12),
    Paragraph("<b>Contents:</b> Lab 10.1 (bank transfer + retry), Lab 10.2 (inventory "
              "reservation, concurrency &amp; throughput), bonus durability/journaling demo.", s["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>How to run the demonstration:</b>", s["Normal"]),
    Paragraph(f"docker run -d --name lab10 {a.image}", mono),
    Paragraph("docker exec -it lab10 /app/run_all.sh", mono),
]
doc.build(story)
print("Created", a.out)
