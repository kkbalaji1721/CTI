#!/bin/bash
/app/start_mongod.sh || exit 1
echo "Lab 10 environment ready. Try:  docker exec -it <container> /app/run_all.sh"
exec "$@"
