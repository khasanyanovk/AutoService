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

if [ "${COLLECTSTATIC:-0}" = "1" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput --clear
fi

echo "Seeding default data (seed_data, fill_car_data)..."
python manage.py seed_data || echo "seed_data failed or already applied, continuing"
python manage.py fill_car_data || echo "fill_car_data failed or already applied, continuing"

if [ "${CREATE_SUPERUSER:-1}" = "1" ]; then
  echo "Ensuring superuser 'admin' exists..."
  python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); u,created=User.objects.get_or_create(username='admin', defaults={'email':'admin@example.com','is_staff':True,'is_superuser':True}); u.is_staff=True; u.is_superuser=True; u.set_password('${ADMIN_PASSWORD:-admin123}'); u.save(); print(f'Superuser \'admin\' {\"created\" if created else \"updated\"} with password.')" || echo "createsuperuser step failed, continuing"
fi

echo "Starting application: $@"
exec "$@"
