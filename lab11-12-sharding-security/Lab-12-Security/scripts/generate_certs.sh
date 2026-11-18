#!/bin/sh
set -eu
cd /certificates

# Local classroom CA. Never use these demo keys in production.
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 \
  -out ca.crt -subj "/CN=MongoDB-Lab-CA"

openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=mongodb"
cat > server.ext <<'EOF'
subjectAltName=DNS:mongodb,DNS:localhost,IP:127.0.0.1
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EOF
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256 -extfile server.ext
cat server.key server.crt > server.pem

openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/CN=lab-client"
cat > client.ext <<'EOF'
extendedKeyUsage=clientAuth
keyUsage=digitalSignature,keyEncipherment
EOF
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out client.crt -days 365 -sha256 -extfile client.ext
cat client.key client.crt > client.pem

# Make the demo files readable by the MongoDB container's non-root process.
chmod 644 ca.crt server.pem client.pem
echo "Created CA, server and client certificate files in /certificates"
