#!/usr/bin/env bash
# exit on error
set -o errexit

# Upgrade packaging tools to ensure wheels can be used when available
python -m pip install --upgrade pip setuptools wheel

# Install requirements using a conservative upgrade strategy
pip install -r requirements.txt --upgrade-strategy only-if-needed

# Collect static files, run migrations, and create admin user
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python create_admin.py
