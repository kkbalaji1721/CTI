# MongoDB 7 image already contains: mongod, mongosh, mongodump, mongorestore
FROM mongo:7.0

ENV PIP_BREAK_SYSTEM_PACKAGES=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONUNBUFFERED=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip \
 && pip3 install --no-cache-dir pymongo tabulate schedule requests reportlab \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY monitor.py backup_verify.py run_demo.sh entrypoint.sh make_pdf.py /app/
RUN chmod +x /app/*.sh && mkdir -p /app/output /data/backups /data/logs

ENTRYPOINT ["/app/entrypoint.sh"]
# Default: run the full demo of both labs, then drop into a shell
CMD ["bash", "-c", "/app/run_demo.sh; exec bash"]
