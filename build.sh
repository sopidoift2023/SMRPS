#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade packaging tools to ensure wheels can be used when available
python -m pip install --upgrade pip setuptools wheel

# If a local wheelhouse directory exists, install from it (no index).
if [ -d "wheelhouse" ]; then
	echo "Using local wheelhouse/ to install wheels"
	pip install --no-index --find-links wheelhouse -r requirements.txt
else
	# Install requirements using a conservative upgrade strategy
	pip install -r requirements.txt --upgrade-strategy only-if-needed
fi

# Collect static files
python manage.py collectstatic --no-input

# Try to connect to the database before running migrations/creating admin.
# If the DB host is not resolvable or connection fails, skip migrations here
# (they should be run later when the DB is reachable).
python - <<'PY'
import os, sys
from urllib.parse import urlparse
url = os.environ.get('DATABASE_URL')
if not url:
	print('No DATABASE_URL set; skipping DB migration in build.')
	sys.exit(2)
u = urlparse(url)
try:
	import psycopg2
	conn = psycopg2.connect(dbname=(u.path or '').lstrip('/'), user=u.username, password=u.password, host=u.hostname, port=u.port or 5432, connect_timeout=5, sslmode='require')
	conn.close()
	print('Database reachable; exiting with 0 so build will run migrations.')
	sys.exit(0)
except Exception as e:
	print('Database not reachable during build (skipping migrations):', e)
	sys.exit(1)
PY

if [ $? -eq 0 ]; then
	python manage.py migrate --no-input
	python create_admin.py
else
	echo "Database not reachable; skipping migrations and admin creation during build."
fi
