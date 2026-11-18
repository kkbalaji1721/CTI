"""Creates Lab15_Submission.pdf containing the Docker Hub URL.
   python make_submission_pdf.py --dockerhub-user jdoe --name "Your Name" --student-id "12345"
"""
import argparse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dockerhub-user", required=True)
    ap.add_argument("--image", default="lab15-multitenant")
    ap.add_argument("--tag", default="latest")
    ap.add_argument("--name", default="")
    ap.add_argument("--student-id", default="")
    ap.add_argument("--out", default="Lab15_Submission.pdf")
    a = ap.parse_args()

    repo = f"{a.dockerhub_user}/{a.image}"
    url = f"https://hub.docker.com/r/{repo}"
    ss = getSampleStyleSheet()
    code = ParagraphStyle("code", parent=ss["Code"], backColor=colors.HexColor("#f3f3f3"), borderPadding=6, fontSize=9)

    s = [Paragraph("Lab 15 - Multi-Tenant API with FastAPI and MongoDB", ss["Title"]),
         Paragraph("Submission: Docker image", ss["Heading2"])]
    if a.name or a.student_id:
        s.append(Paragraph(f"<b>Student:</b> {a.name} &nbsp;&nbsp; <b>ID:</b> {a.student_id}", ss["Normal"]))
    s += [Spacer(1, 10),
          Paragraph("<b>Docker Hub URL:</b>", ss["Normal"]),
          Paragraph(f'<link href="{url}" color="blue"><u>{url}</u></link>', ParagraphStyle("u", parent=ss["Normal"], fontSize=13, spaceBefore=4)),
          Spacer(1, 12),
          Paragraph("Run the full demonstration (tests, Lab 15.1 demo, Lab 15.2):", ss["Heading3"]),
          Preformatted(f"docker run --rm {repo}:{a.tag} all", code),
          Spacer(1, 6),
          Paragraph("Start the API (Swagger UI at http://localhost:8000/docs):", ss["Heading3"]),
          Preformatted(f"docker run --rm -p 8000:8000 --name lab15 {repo}:{a.tag}\n"
                       "docker exec lab15 python scripts/demo_15_1.py\n"
                       "docker exec lab15 python -m lab15_2.run_all", code),
          Spacer(1, 10),
          Paragraph("What the image contains", ss["Heading3"])]
    rows = [["Task", "Implementation"],
            ["15.1 Schema + tenant isolation", "tenant_id on every document; compound index (tenant_id, created_at)"],
            ["15.1 CRUD", "tenant_id taken from the JWT; filter applied on every query"],
            ["15.1 Rate limiting", "rate_limits collection, atomic findAndModify counter, TTL index"],
            ["15.1 Activity (RBAC)", "admin: all tenant tasks; user: only own tasks"],
            ["15.2 Migration", "5 tenants x 100 tasks; $out / insert_many to tasks_tenant_<id>"],
            ["15.2 Validation", "counts, id equality, no cross-tenant leakage"],
            ["15.2 Comparison + recommendation", "benchmark report and docs/RECOMMENDATION.md"]]
    rows = [[Paragraph(c, ss["BodyText"]) for c in r] for r in rows]
    t = Table(rows, colWidths=[5.5 * cm, 11 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde6f2")),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    s.append(t)
    SimpleDocTemplate(a.out, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                      title="Lab 15 Submission", author=a.name or a.dockerhub_user).build(s)
    print(f"Created {a.out}\nDocker URL in PDF: {url}")


if __name__ == "__main__":
    main()
