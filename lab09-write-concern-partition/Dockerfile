FROM python:3.12-slim

# Name this image will be published under (used to bake a ready-to-run compose file)
ARG IMAGE_NAME=nosql-lab09:latest

# Docker CLI only (needed by Lab 9.2 to disconnect/reconnect containers from the network)
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /lab
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /lab/
COPY docker-compose.yml /lab/docker-compose.template.yml
RUN sed "s|nosql-lab09:latest|${IMAGE_NAME}|g" /lab/docker-compose.template.yml > /lab/docker-compose.yml

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-u", "/lab/lab.py"]
CMD ["help"]
