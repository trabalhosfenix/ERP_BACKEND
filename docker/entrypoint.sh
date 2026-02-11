#!/bin/bash
set -e

echo "Waiting for MySQL at ${DB_HOST}:${DB_PORT}..."
python - <<'PY'
import os, time, sys
import MySQLdb

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", "3306"))
user = os.getenv("DB_USER", "root")
passwd = os.getenv("DB_PASSWORD", "root")
db = os.getenv("DB_NAME", "erp")

deadline = time.time() + 90
while True:
    try:
        conn = MySQLdb.connect(host=host, port=port, user=user, passwd=passwd, db=db, connect_timeout=2)
        conn.close()
        break
    except Exception as e:
        if time.time() > deadline:
            print("MySQL not ready:", repr(e))
            sys.exit(1)
        time.sleep(2)
print("MySQL is ready.")
PY

echo "Running migrations..."
python manage.py migrate --noinput

exec "$@"
