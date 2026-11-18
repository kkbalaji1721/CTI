"""Build the submission PDF from measured benchmark output and project status."""

import csv
import os
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
SUBMISSION = ROOT / "submission"
SUBMISSION.mkdir(exist_ok=True)
PDF = SUBMISSION / "Lab17_Submission_Report.pdf"
DOCKER_URL = os.getenv(
    "DOCKERHUB_URL", "https://hub.docker.com/r/kkbalaji1721/mongodb-lab17"
)
DOCKER_STATUS = (
    "An earlier Docker image was published to Docker Hub, but upload of the updated two-lab image "
    "was unsuccessful. This report does not claim that the updated image was published."
)
TEST_STATUS = os.getenv(
    "LAB17_TEST_STATUS",
    "Run `python -m unittest -v test_lab17.py` to verify the current source.",
)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=24, leading=30))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))

story = [
    Spacer(1, 0.8 * inch),
    Paragraph("MongoDB NoSQL Database Lab 17", styles["CoverTitle"]),
    Paragraph("Threat Intelligence RAG and Vector Index Benchmark", styles["Heading2"]),
    Spacer(1, 0.3 * inch),
    Paragraph(f"Submission report | Generated {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}", styles["Normal"]),
    Spacer(1, 0.35 * inch),
    Paragraph(
        "Status note: this workspace had no MongoDB Atlas URI, Voyage key, or LLM API key. "
        "Therefore Atlas operations and LLM/API results are not represented as successful. "
        "Offline behavior and local benchmark values below were generated from the included code.",
        styles["BodyText"],
    ),
    Spacer(1, 0.3 * inch),
    Paragraph("1. Lab 17.1 objective", styles["Heading1"]),
    Paragraph(
        "Implement a retrieval-augmented generation flow for threat intelligence: split source "
        "documents into overlapping chunks, embed and retrieve relevant context, answer a query, "
        "and retain recent conversation messages.",
        styles["BodyText"],
    ),
    Paragraph("2. Implementation and architecture", styles["Heading1"]),
    Paragraph(
        "Five short threat-intelligence notes cover ransomware/VPN access, phishing loaders, cloud "
        "identity, Linux web shells, and software supply chains. Text is split into 100-word windows "
        "with 20-word overlap. Voyage AI is selected when VOYAGE_API_KEY is present; its model-specific "
        "dimension is used in the Atlas index. Otherwise the explicitly labeled local fallback is a "
        "deterministic 384-dimensional hashed text-feature vector (not a learned semantic embedding).",
        styles["BodyText"],
    ),
    Paragraph(
        "Flow: threat reports → sliding-window chunks → embeddings → rag_documents → top-3 vector "
        "retrieval → retrieved context + last five messages → configurable OpenAI-compatible LLM. "
        "Atlas mode issues MongoDB's $vectorSearch stage and stores conversation messages in the "
        "conversations collection. With no Atlas URI, this workspace runs exact cosine retrieval "
        "and process-local memory, and clearly does not claim to execute $vectorSearch.",
        styles["BodyText"],
    ),
    Paragraph("3. Conversation memory", styles["Heading1"]),
    Paragraph(
        "Each successful turn stores a user and assistant message. The next prompt includes up to "
        "the last five messages. Atlas persists a bounded 100-message list per conversation; local "
        "demonstration memory exists only for the current process.",
        styles["BodyText"],
    ),
    Paragraph(
        "Automated validation: " + TEST_STATUS + " Tests cover local recall of a previous question, "
        "per-session isolation, conversation prompt history, embedding dimensions, and chunk overlap.",
        styles["BodyText"],
    ),
    Paragraph("4. Lab 17.2 objective and method", styles["Heading1"]),
    Paragraph(
        "The benchmark uses 5,000 deterministic threat-report documents, 384-dimensional feature "
        "vectors, 100 queries, and exact cosine top-20 as ground truth. Recall is the mean of "
        "|approximate top-20 ∩ exact top-20| / 20 × 100. IVF uses MiniBatchKMeans clusters; the "
        "HNSW-style comparison is a single-layer navigable graph implementation for instruction, "
        "not a production HNSW library or Atlas measurement. Timings are local, machine-specific "
        "measurements.",
        styles["BodyText"],
    ),
    Paragraph("5. Measured local comparison", styles["Heading1"]),
]

csv_path = RESULTS / "comparison.csv"
if csv_path.exists():
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required_columns = {
        "index",
        "build_time_seconds",
        "avg_query_latency_ms",
        "recall_at_20_percent",
        "avg_vectors_examined",
    }
    if not rows or not required_columns.issubset(rows[0]):
        raise ValueError(f"{csv_path} is missing benchmark rows or required columns")

    header_style = ParagraphStyle(
        name="TableHeader",
        parent=styles["Small"],
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    data = [[
        Paragraph("Search Method", header_style),
        Paragraph("Build Time (s)", header_style),
        Paragraph("Average Query Latency (ms)", header_style),
        Paragraph("Recall@20 (%)", header_style),
        Paragraph("Average Vectors Examined", header_style),
    ]]
    for row in rows:
        data.append(
            [
                row["index"],
                f'{float(row["build_time_seconds"]):.4f}',
                f'{float(row["avg_query_latency_ms"]):.4f}',
                f'{float(row["recall_at_20_percent"]):.2f}',
                f'{float(row["avg_vectors_examined"]):.2f}',
            ]
        )
    table = Table(
        data,
        colWidths=[92, 75, 141, 80, 130],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183153")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3f8")]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([table, Spacer(1, 0.15 * inch)])
else:
    story.append(Paragraph("Benchmark results not generated; run python benchmark.py.", styles["BodyText"]))

graph = RESULTS / "latency_vs_recall.png"
if graph.exists():
    story.extend([
        Paragraph("Latency versus recall", styles["Heading2"]),
        KeepTogether([Image(str(graph), width=6.4 * inch, height=4.0 * inch)]),
    ])
story.extend([
    Paragraph(
        "Interpretation: compare measured build time, query latency, recall, and vectors examined "
        "together. IVF is useful when cluster partitioning and tunable probes fit the workload; "
        "HNSW is a common choice for high-recall, low-latency ANN at memory cost. These local "
        "educational implementations do not establish production or Atlas performance.",
        styles["BodyText"],
    ),
    Paragraph("6. MongoDB Atlas compatibility and limitations", styles["Heading1"]),
    Paragraph(
        "No Atlas URI was configured, so actual deployment/version capabilities, index creation, "
        "document insertion, and $vectorSearch were not tested. No successful Atlas IVF index is "
        "claimed. The included Atlas RAG path requests a vectorSearch index and relies on Atlas's "
        "supported API, but must be run against the learner's deployment to verify the result.",
        styles["BodyText"],
    ),
    Paragraph("7. Docker implementation", styles["Heading1"]),
    Paragraph(
        "The Dockerfile installs requirements.txt, including PyMongo, NumPy, scikit-learn, Matplotlib, "
        "python-dotenv, and ReportLab, and copies the Python scripts for both labs. Benchmark outputs "
        "are generated at run time; .env, caches, datasets, and VCS files are excluded from the build "
        "context. Credentials are passed at runtime. " + DOCKER_STATUS,
        styles["BodyText"],
    ),
    Paragraph(f"Docker Hub repository: {DOCKER_URL}", styles["BodyText"]),
    Paragraph("8. Run commands", styles["Heading1"]),
    Paragraph(
        "python -m pip install -r requirements.txt<br/>"
        "python app.py<br/>"
        "python generate_dataset.py<br/>"
        "python benchmark.py<br/>"
        "python build_report.py<br/>"
        "docker build -t mongodb-lab17 .<br/>"
        "docker run --rm -it mongodb-lab17 python app.py<br/>"
        "docker run --rm -v &lt;workspace&gt;\\results:/app/results mongodb-lab17 python benchmark.py",
        styles["Code"],
    ),
    Paragraph("9. Screenshots to capture manually", styles["Heading1"]),
    Paragraph(
        "No screenshots were fabricated. If your instructor requires visual evidence, manually "
        "capture: (1) an Atlas Vector Search index in READY state and a successful query after you "
        "configure Atlas; (2) a two-turn RAG session showing follow-up memory; and (3) the Docker Hub "
        "repository page after the updated two-lab image has been successfully pushed. Atlas remains "
        "unverified in this run.",
        styles["BodyText"],
    ),
    Paragraph("10. Conclusion", styles["Heading1"]),
    Paragraph(
        "This submission provides independently runnable RAG, conversation-memory, reproducible "
        "benchmark, Docker and reporting implementations. Offline tests and results are explicitly "
        "separated from external service actions. Configure Atlas and API credentials to complete "
        "live database and model demonstrations; publish the image only after Docker Hub login.",
        styles["BodyText"],
    ),
])

doc = SimpleDocTemplate(
    str(PDF), pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch,
    topMargin=0.6 * inch, bottomMargin=0.6 * inch, title="MongoDB NoSQL Database Lab 17",
)
doc.build(story)
print(f"Created {PDF}")
