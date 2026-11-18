#!/usr/bin/env bash
# Entry point of the lab image. Starts an embedded MongoDB (unless MONGO_URI points elsewhere), then runs a command.
set -euo pipefail

CMD="${1:-api}"
APP_PORT="${PORT:-8000}"

start_mongo() {
  if [ -n "${MONGO_URI:-}" ]; then
    echo "[lab15] using external MongoDB: ${MONGO_URI}"
  else
    echo "[lab15] starting embedded MongoDB ..."
    mkdir -p /data/db
    mongod --bind_ip 127.0.0.1 --dbpath /data/db --fork --logpath /var/log/mongod.log --quiet >/dev/null
    export MONGO_URI="mongodb://127.0.0.1:27017"
  fi
  for i in $(seq 1 40); do
    if python -c "from pymongo import MongoClient; MongoClient('${MONGO_URI}', serverSelectionTimeoutMS=500).admin.command('ping')" 2>/dev/null; then
      echo "[lab15] MongoDB is ready"; return 0
    fi
    sleep 0.5
  done
  echo "[lab15] ERROR: MongoDB did not become ready"; exit 1
}

start_api_bg() {
  uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT}" --log-level warning &
  API_PID=$!
  for i in $(seq 1 40); do
    if python -c "import httpx,sys; sys.exit(0 if httpx.get('http://127.0.0.1:${APP_PORT}/health',timeout=1).status_code==200 else 1)" 2>/dev/null; then return 0; fi
    sleep 0.5
  done
  echo "[lab15] ERROR: API did not start"; kill "$API_PID" 2>/dev/null || true; exit 1
}

case "$CMD" in
  api)
    start_mongo
    echo "[lab15] API on http://localhost:${APP_PORT}   (Swagger UI: /docs)"
    exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT}"
    ;;
  demo-15-1)      # start API in background, run the live demo, exit with its status
    start_mongo; start_api_bg
    set +e; python scripts/demo_15_1.py "http://127.0.0.1:${APP_PORT}"; rc=$?
    kill "$API_PID" 2>/dev/null || true; exit $rc
    ;;
  lab15-2)        # seed -> migrate -> validate -> benchmark
    start_mongo
    shift || true
    exec python -m lab15_2.run_all "$@"
    ;;
  test)           # unit tests (mongomock - no database needed)
    exec python -m pytest -q tests -p no:cacheprovider
    ;;
  all)            # everything once, in order - ideal for a grader/demo run
    start_mongo
    echo; echo "################ UNIT TESTS ################"
    python -m pytest -q tests -p no:cacheprovider -W ignore
    echo; echo "################ LAB 15.1 DEMO ################"
    start_api_bg
    python scripts/demo_15_1.py "http://127.0.0.1:${APP_PORT}"
    kill "$API_PID" 2>/dev/null || true
    echo; echo "################ LAB 15.2 ################"
    python -m lab15_2.run_all
    ;;
  bash|sh)
    start_mongo
    exec /bin/bash
    ;;
  *)
    exec "$@"
    ;;
esac
