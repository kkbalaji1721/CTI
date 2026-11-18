# Lab 1 – NoSQL Families: Classification & Mapping

**Student:** Kothakuruva Balaji (24BTRCL104)

## Objective
- **Lab 1.1** – Classify real-world database products into NoSQL families (Document, Key-Value, Wide-Column, Graph …).
- **Lab 1.2** – Map the data domains of real applications to the most suitable NoSQL family.

## Structure
```
code/
  lab1_1_classify_products.py     # Lab 1.1 – 10 products -> nosql_labs.database_products
  lab1_1_try_it_yourself.py       # Lab 1.1 – Try It Yourself (more products)
  lab1_2_map_applications.py      # Lab 1.2 – app domains -> nosql_labs.app_domain_mapping
  lab1_2_try_it_yourself.py       # Lab 1.2 – Try It Yourself (more applications)
config/connection.py              # get_db / reset_collection / banner helpers
data/                             # exported MongoDB collections (JSON results)
reports/                          # Lab1.1_Report.docx, Lab1.2_Report.docx
requirements.txt
```

## Setup
```bash
pip install -r requirements.txt      # pymongo, rich
```
MongoDB must be running on `localhost:27017` (override with `MONGO_HOST` / `MONGO_PORT`). Database used: `nosql_labs`.

## Run
```bash
cd code
python lab1_1_classify_products.py
python lab1_2_map_applications.py
```
