"""Creates the PDF to submit.   pip install reportlab   then:
       python make_submission_pdf.py YOUR_DOCKERHUB_USERNAME "Your Name"
"""
import sys

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

user = sys.argv[1] if len(sys.argv) > 1 else "YOUR_DOCKERHUB_USERNAME"
name = sys.argv[2] if len(sys.argv) > 2 else ""
url = f"https://hub.docker.com/r/{user}/nosql-lab16"

c = canvas.Canvas("Lab16_Submission.pdf", pagesize=A4)
w, h = A4
y = h - 80
c.setFont("Helvetica-Bold", 18); c.drawString(60, y, "Chapter 16 - NoSQL Lab Submission"); y -= 40
c.setFont("Helvetica", 12)
if name:
    c.drawString(60, y, f"Student: {name}"); y -= 30
c.drawString(60, y, "Tasks completed: Lab 16.1, Activity 16.1, Lab 16.2"); y -= 30
c.drawString(60, y, "Docker Hub image URL:"); y -= 22
c.setFillColorRGB(0, 0, 0.8); c.drawString(60, y, url)
c.linkURL(url, (60, y - 4, 60 + c.stringWidth(url, "Helvetica", 12), y + 12)); y -= 40
c.setFillColorRGB(0, 0, 0)
c.drawString(60, y, "Pull command:"); y -= 20
c.setFont("Courier", 11); c.drawString(60, y, f"docker pull {user}/nosql-lab16:latest"); y -= 40
c.setFont("Helvetica", 12)
for line in ["Demonstration:",
             "  1. Download docker-compose.yml (shown on the Docker Hub page)",
             "  2. docker compose up",
             "  The container waits for MongoDB, Cassandra and Neo4j, then runs all lab tasks."]:
    c.drawString(60, y, line); y -= 18
c.save()
print("Created Lab16_Submission.pdf with URL", url)
