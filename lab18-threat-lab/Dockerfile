FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pymongo cassandra-driver neo4j networkx reportlab
COPY lab.py docker-compose.yml README.md /app/
CMD ["python", "lab.py"]
