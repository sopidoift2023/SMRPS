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

# Collect static files, run migrations, and create admin user
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python create_admin.py
