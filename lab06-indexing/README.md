# Lab 6 – Index Design & Index Strategies

**Course:** NoSQL Databases · **Student:** Kothakuruva Balaji (24BTRCL104)

## Objective
- **Lab 6.1** – Design indexes for query patterns; measure usage with `$indexStats`.
- **Lab 6.2** – Compare index strategies (write throughput vs read performance); verify covered queries and the absence of a `FETCH` stage.

## Files
| File | Purpose |
|------|---------|
| `lab_01_index_design.py` | Lab 6.1 – index design |
| `lab_01_tryityourself.py` | Lab 6.1 – `$indexStats` usage measurement |
| `lab_02_index_strategies.py` | Lab 6.2 – strategy comparison |
| `lab_02_tryityourself.py` | Lab 6.2 – covered query / FETCH stage verification |
| `config/connection.py` | DB helper (`MONGO_HOST`, `MONGO_PORT`, default `localhost:27017`) |
| `Lab6_Report_24BTRCL104.docx` | Written report |

## Setup & Run
```bash
pip install pymongo
python lab_01_index_design.py
python lab_02_index_strategies.py
```
