#!/usr/bin/env sh
set -e

echo "Waiting for database..."
while ! nc -z "${DB_HOST:-db}" "${DB_PORT:-5432}"; do
  echo "Database is unavailable - sleeping"
  sleep 1
done
echo "Database is up - continuing"

echo "Applying database migrations..."
python manage.py migrate --noinput


echo "Collecting static files..."
python manage.py collectstatic --noinput --clear


echo "Seeding default data (seed_data, fill_car_data)..."
python manage.py seed_data || echo "seed_data failed or already applied, continuing"
python manage.py fill_car_data || echo "fill_car_data failed or already applied, continuing"

echo "Starting application: $@"
exec "$@"
