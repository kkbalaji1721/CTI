#!/bin/bash
# Copy the shared keyfile into place with the permissions mongod requires, then
# hand over to the official entrypoint (which drops privileges to user mongodb).
set -e
if [ -f /keyfile-src/keyfile ]; then
  mkdir -p /etc/mongodb
  cp /keyfile-src/keyfile /etc/mongodb/keyfile
  chown mongodb:mongodb /etc/mongodb/keyfile
  chmod 400 /etc/mongodb/keyfile
fi
exec docker-entrypoint.sh "$@"
