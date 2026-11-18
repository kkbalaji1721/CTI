# One image = embedded MongoDB + Python app + lab scripts, so `docker run` works with nothing else installed.
FROM mongo:7

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    RESULTS_DIR=/app/results

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m venv /opt/venv

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY lab15_2 ./lab15_2
COPY scripts ./scripts
COPY tests ./tests
COPY docs ./docs
COPY README.md .
COPY docker-entrypoint-lab.sh /usr/local/bin/docker-entrypoint-lab.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-lab.sh && mkdir -p /app/results

EXPOSE 8000
VOLUME ["/data/db"]
ENTRYPOINT ["docker-entrypoint-lab.sh"]
CMD ["api"]
