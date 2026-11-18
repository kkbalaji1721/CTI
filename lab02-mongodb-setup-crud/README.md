# Lab 2 – MongoDB Environment Setup & Bookstore CRUD

**Course:** NoSQL Databases · **Student:** Kothakuruva Balaji (24BTRCL104)

## Objective
- **Lab 2.1** – Verify the environment (Python, pymongo, MongoDB connectivity) and compare a local/Docker MongoDB with MongoDB Atlas.
- **Lab 2.2** – Implement full CRUD on a bookstore collection.

## Structure
```
NoSql_lab2/              # Lab 2.1
  code/first_connection.py            # connectivity check + server info
  code/lab_01_setup_environment.py    # environment verification -> JSON
  code/lab_01_try_it_yourself.py      # Local vs Atlas comparison via server_info()
  config/connection.py                # connection helper (reads env vars)
NoSql_lab2.2/            # Lab 2.2
  code/lab_02_bookstore_crud.py       # insert 5 books, queries, +10% price update, delete
  code/lab_02_try_it_yourself.py      # +10% price for books published before 2010
Lab2_Report_24BTRCL104.docx   # written report
```
`*.json` files are exported results of each script.

## Setup
1. Install Python 3.10+ and `pip install pymongo python-dotenv`.
2. Start a local MongoDB, **or** use MongoDB Atlas.
3. For Atlas, copy `.env.example` to `.env` and set your own connection string:
   ```
   MONGO_URI_ATLAS=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
   ```
   > ⚠️ Never commit `.env` – it is git-ignored.

## Run
```bash
cd NoSql_lab2/code   && python first_connection.py
cd NoSql_lab2.2/code && python lab_02_bookstore_crud.py
```
