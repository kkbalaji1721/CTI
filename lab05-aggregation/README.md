# Lab 5 - Aggregation Pipelines and $lookup Joins

## Folder layout
| Folder | Python script | MongoDB data file (JSON) |
|---|---|---|
| Activity_5.1_Sales_Analytics_Pipeline | lab_5_1_sales_analytics.py | lab_5_1_orders.json |
| Activity_5.1_Try_It_Yourself_Bucket | lab_5_1_try_it_bucket.py | lab_5_1_try_it_orders.json |
| Activity_5.2_Lookup_Joins | lab_5_2_lookup_joins.py | lab_5_2_data.json |
| Activity_5.2_Try_It_Yourself_Lookup_SubPipeline | lab_5_2_try_it_lookup_subpipeline.py | lab_5_2_try_it_data.json |

`Lab5_Report_Scripts_and_Outputs.docx` contains every script and its output screenshot.

## How to run
1. Start MongoDB (local `mongod` on port 27017, or MongoDB Atlas).
2. `pip install pymongo`
3. Open a terminal inside an activity folder and run its script, e.g.
   `python lab_5_1_sales_analytics.py`

Using Atlas or another host? Set the connection string first:
- Windows (cmd):  `set MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net`
- Windows (PowerShell): `$env:MONGO_URI="mongodb+srv://..."`
- macOS / Linux: `export MONGO_URI="mongodb+srv://..."`

Each script drops and re-creates its own collections, so it can be run any number of times.
Databases used: lab5_1_sales, lab5_1_bucket, lab5_2_lookup, lab5_2_subpipeline.

## JSON data files
Each file looks like `{"orders": [...]}` (5.2 also has `"products"`). Dates are stored as
`{"$date": "2026-01-05T00:00:00Z"}` (MongoDB Extended JSON), which the scripts convert to real
Date values. To import manually with MongoDB tools you can copy one array into its own file and run
`mongoimport --db mydb --collection orders --jsonArray --file orders.json`.
