# Lab 2.1 – Environment Setup Verification

Verifies Python/pymongo/MongoDB connectivity and compares a local/Docker MongoDB with MongoDB Atlas.

| File | Purpose |
|------|---------|
| `code/first_connection.py` | Connect to MongoDB and print server info |
| `code/lab_01_setup_environment.py` | Check tools/connections, save result to `lab_01_setup_environment.json` |
| `code/lab_01_try_it_yourself.py` | Local vs Atlas comparison via `server_info()` -> `lab_01_try_it_yourself.json` |
| `config/connection.py` | Connection helper (reads `.env`) |

**Run:** `pip install pymongo python-dotenv`, copy `../.env.example` to `.env` (Atlas only), then `cd code && python first_connection.py`.
