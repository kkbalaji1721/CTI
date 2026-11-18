# Python 3.11 is used because cassandra-driver does not yet support 3.12+ out of the box
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

LABEL description="Chapter 16 NoSQL Lab: Lab 16.1 (3-DB modelling) and Lab 16.2 (FraudQueryService)"

# Default: wait for the 3 databases, seed data, run ALL lab tasks, save results to /app/output
CMD ["python", "run_all.py"]
