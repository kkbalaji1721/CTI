# Lab 7.1 - Production schema analysis
_Generated 2026-10-11 04:44 UTC; source: built-in sample_

## Embedding vs referencing

| Relationship | Choice | Why |
|---|---|---|
| threat -> iocs | **Embedded** | Always read with the threat, bounded size, 1:few. |
| threat -> classification | **Embedded** | 1:1, computed at ingest, filtered/indexed in place. |
| threat -> tags | **Embedded** | Small array; multikey index. |
| threat -> source | **Referenced** (`source_id`) | See below. |

| vulnerability -> threats | **Referenced** (`threat_ids`) | Many:many; a CVE appears in many threats and a threat names several CVEs. `_id` = CVE id, so a CVE is stored once. |
| threat -> iocs (dedupe) | **Embedded, set-deduplicated** | Each IOC value is stored once per threat. |

## Duplicate removal

- Received 10; duplicates inside the batch: **2**; already in DB: 0; inserted: **8**.
- A duplicate = same normalised title (`title_key`) or same normalised URL (`url_key`: no scheme, `www`, query string, fragment or trailing slash). The highest-scoring copy is kept.
- A unique index on `title_key` stops duplicates at database level. Existing data: `python labs/dedupe_existing.py`.

## Vulnerabilities

- 2 unique CVEs, 2 flagged as exploited in the wild (CVSS filled with `--nvd`).

## Why `source` is referenced, and the embedded alternative

- One source has hundreds of threats; embedding duplicates name/URL/reliability in every document.
- Reliability is updated over time; with embedding a change means `updateMany` over all threats and risks stale copies.
- Alternative (built as `threats_embedded`): `{ ..., source: {name, reliability}, is_actual_threat: true }`.

## Activity 7.1 - embedded source to decide the 'actual threat'

- **Faster:** the dashboard, filters like `{is_actual_threat: true}` and sort by score need one collection, no `$lookup`.
- **Harder:** updating a source's reliability must rewrite every embedded copy; the verdict can go stale; documents grow slightly.
- Hybrid used in production: reference the source *and* embed a snapshot (`name`, `reliability`) that is refreshed in a batch job.

## Document sizes (`$bsonSize`)

| Collection | Docs | Avg bytes | Max bytes | Max as % of 16 MB |
|---|---|---|---|---|
| threats | 8 | 564 | 665 | 0.0040% |
| threats_embedded | 8 | 639 | 741 | 0.0044% |
| vulnerabilities | 2 | 231 | 233 | 0.0014% |
| sources | 5 | 98 | 117 | 0.0007% |

No document approaches the 16 MB limit.
