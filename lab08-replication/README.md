# Lab 8 – Replication (MongoDB Replica Sets with Docker)

**Course:** NoSQL Databases · **Student:** Kothakuruva Balaji (24BTRCL104)

## Objective
Deploy a MongoDB replica set with Docker, add an arbiter, observe automatic failover/step-down, and control elections with member priorities.

## Activities
| Folder | Description |
|--------|-------------|
| `Activity_8.1/` | Deploy a replica set + initialise it |
| `Activity_8.1_Try_It_Yourself/` | Add an arbiter |
| `Activity_8.2/` | Failover observer & step-down |
| `Activity_8.2_Try_It_Yourself/` | Member priority configuration |
| `Lab8_Report_24BTRCL104.docx` | Written report |

## Prerequisites
Docker Desktop (engine running) and `pip install -r requirements.txt`.

## Run (one folder at a time, in order)
```bash
cd Activity_8.1                  && python lab_8_1_deploy_replicaset.py
cd Activity_8.1_Try_It_Yourself  && python lab_8_1_try_it_arbiter.py
cd Activity_8.2                  && python lab_8_2_failover_observer.py
cd Activity_8.2_Try_It_Yourself  && python lab_8_2_try_it_priority.py
```
Containers publish on `localhost:28017-28019` so they don't clash with a local MongoDB.

## Clean up
```bash
docker compose -p mongo-rs-lab -f docker-compose.yml down -v
```
See `README_original.txt` for the original submission notes.
