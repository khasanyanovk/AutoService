#!/usr/bin/env sh
set -e

if [ "${COLLECTSTATIC:-0}" = "1" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi


echo "Applying database migrations..."
python manage.py migrate --noinput


echo "Seeding default data (seed_data, fill_car_data)..."
python manage.py seed_data || echo "seed_data failed or already applied, continuing"
python manage.py fill_car_data || echo "fill_car_data failed or already applied, continuing"

echo "Ensuring superuser 'admin' exists..."
python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); u,created=User.objects.get_or_create(username='admin', defaults={'email':'admin@example.com','is_staff':True,'is_superuser':True}); u.is_staff=True; u.is_superuser=True; u.set_password('password'); u.save(); print(f'Superuser \'admin\' {\"created\" if created else \"updated\"} with default password.')" || echo "createsuperuser step failed, continuing"


echo "Starting application: $@"
exec "$@"
