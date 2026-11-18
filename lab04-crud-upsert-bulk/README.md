# Lab 4 – Product Query API, Upserts & Bulk Operations

**Course:** NoSQL Databases · **Student:** Kothakuruva Balaji (24BTRCL104)

## Objective
- **Lab 4.1** – Build a product query API: CRUD with comparison, logical and array operators, projections and pagination.
- **Lab 4.2** – Implement upserts and bulk operations (conditional inserts + batch modifications).

## Structure
```
NoSql_lab4.1/
  code/lab_01_product_query_api.py          # query API (reference solution)
  code/lab_4.1_product_inventory_crud.py    # product inventory CRUD
  code/4.1_try_it_yourself.py           # Try It Yourself
  code/nosql_labs.products.json             # exported collection
  code/Lab4.1_Report_24BTRCL104.docx
  config/connection.py
NoSql_lab4.2/
  code/lab_02_upsert_bulk.py / lab_4.2_upsert_bulk.py   # upsert + bulk_write
  code/4.2_try_it_yourself.py
  code/nosql_labs.inventory.json
  code/Lab4.2_Report_24BTRCL104.docx
  config/connection.py
```

## Setup & Run
```bash
pip install pymongo rich
cd NoSql_lab4.1/code && python lab_01_product_query_api.py
cd ../../NoSql_lab4.2/code && python lab_02_upsert_bulk.py
```
Requires MongoDB on `localhost:27017` (override with `MONGO_HOST` / `MONGO_PORT`).
