# Lab 3 – Document Schema Design (Embedding vs Referencing)

**Course:** NoSQL Databases · **Student:** Kothakuruva Balaji (24BTRCL104)

## Objective
Practise choosing between **embedded** and **referenced** document models, and handle media/binary data.

## Activities
| Folder | Description |
|--------|-------------|
| `Activity_3.1_Embedded_Schema/` | University course-enrollment system using an embedded document schema |
| `Activity_3.1_TryItYourself_Prerequisites/` | Course prerequisites – embed vs reference, with justification |
| `Activity_3.2_Referenced_To_Embedded/` | Blog posts + comments: migrate a referenced design to an embedded one |
| `Activity_3.2_TryItYourself_10000_Comments/` | Why embedding fails for a post with 10,000 comments; bucket/reference alternative |
| `media_utils.py`, `pixel_image_storage.py` | Helpers for storing image/video data |
| `media/` | Sample `photo.jpg` and `minivideo.mp4` |
| `Lab3_Report_24BTRCL104.docx` | Written report |

JSON files in each folder are sample inputs/outputs.

## Setup & Run
```bash
pip install pymongo
cd Activity_3.1_Embedded_Schema
python lab_3_1_embedded_schema.py
```
Each activity folder is run the same way from inside its own folder (MongoDB on `localhost:27017`).
