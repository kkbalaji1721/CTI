# MongoDB Labs 11 and 12 — Final Report

**Student Name:** __________________________  
**USN:** __________________________  
**Course / Section:** __________________________  
**Docker Hub URL:** `https://hub.docker.com/r/YOUR_USERNAME/mongodb-lab11-12`

## Objective
To evaluate shard-key strategies, observe hotspot behaviour, configure MongoDB authentication and role-based access control, and verify TLS encryption in transit.

## Lab 11.1 — Evaluate Shard Key Choices
Insert the decision matrix and resharding activity from `Lab-11-Sharding/LAB11_1_DECISION_MATRIX.md`.

## Lab 11.2 — Hotspot Detection
**Environment:** MongoDB version ______ / Docker version ______

**Actual document counts**
- hotspot_data: ______
- even_data: ______

**Actual per-shard statistics:** Attach screenshot(s).

**Explain output:** Attach screenshots for both range queries.

**Observation:** Explain whether timestamp inserts concentrated on one shard and whether the hashed collection was more evenly distributed. State actual observations; do not copy expected sample numbers as measured facts.

## Lab 12.1 — Authentication and RBAC
Record evidence for:
- root authentication succeeds.
- orders_reader can read orders_public but cannot write.
- orders_writer can write orders but cannot read employees.
- hr_reader can read employees_public without salary and cannot query employees directly.

Attach successful and denied operation screenshots.

## Lab 12.2 — TLS
Record evidence for:
- CA, server and client certificate files generated.
- plaintext connection rejected.
- TLS connection ping succeeded.
- TLS-protected insert succeeded.

Attach the Python test output and certificate-chain summary (do not include private key contents).

## Conclusion
Summarize what was learned about shard-key trade-offs, write hotspots, least-privilege access, field redaction through views, and TLS encryption.

## Docker Hub
**Repository:** __________________________  
**Image tag:** __________________________  
**Public/Private:** __________________________  
**Demonstration instructions:** Run the relevant Docker Compose project using the supplied README.

## Appendix — Evidence
Paste screenshots from your own completed runs here.
