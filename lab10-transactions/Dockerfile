FROM mongo:7.0

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip procps \
 && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir "pymongo>=4.6,<5" matplotlib

WORKDIR /app
COPY *.py *.sh /app/
RUN sed -i 's/\r$//' /app/*.sh /app/*.py && chmod +x /app/*.sh /app/*.py && mkdir -p /app/results

EXPOSE 27017
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
