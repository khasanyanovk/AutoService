from django.core.management.base import BaseCommand
from core.models import ServiceType, WorkingHours


class Command(BaseCommand):
    help = "Заполняет базу данных типами услуг и рабочим временем"

    def handle(self, *args, **options):
        services = [
            {
                "name": "Техническое обслуживание",
                "description": "Регулярное техническое обслуживание автомобиля",
                "duration": 120,
                "price": 5000,
            },
            {
                "name": "Замена масла",
                "description": "Замена моторного масла и фильтра",
                "duration": 60,
                "price": 2500,
            },
            {
                "name": "Диагностика",
                "description": "Полная компьютерная диагностика автомобиля",
                "duration": 90,
                "price": 3000,
            },
            {
                "name": "Замена тормозных колодок",
                "description": "Замена передних и задних тормозных колодок",
                "duration": 120,
                "price": 4000,
            },
            {
                "name": "Развал-схождение",
                "description": "Регулировка углов установки колес",
                "duration": 90,
                "price": 3500,
            },
        ]

        for service_data in services:
            service, created = ServiceType.objects.get_or_create(
                name=service_data["name"], defaults=service_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Добавлена услуга: {service_data["name"]}')
                )

        working_hours = [
            {
                "day_of_week": 1,
                "start_time": "09:00",
                "end_time": "18:00",
                "is_working": True,
            },
            {
                "day_of_week": 2,
                "start_time": "09:00",
                "end_time": "18:00",
                "is_working": True,
            },
            {
                "day_of_week": 3,
                "start_time": "09:00",
                "end_time": "18:00",
                "is_working": True,
            },
            {
                "day_of_week": 4,
                "start_time": "09:00",
                "end_time": "18:00",
                "is_working": True,
            },
            {
                "day_of_week": 5,
                "start_time": "09:00",
                "end_time": "18:00",
                "is_working": True,
            },
            {
                "day_of_week": 6,
                "start_time": "10:00",
                "end_time": "16:00",
                "is_working": True,
            },
            {
                "day_of_week": 7,
                "start_time": "10:00",
                "end_time": "14:00",
                "is_working": False,
            },
        ]

        for wh_data in working_hours:
            wh, created = WorkingHours.objects.get_or_create(
                day_of_week=wh_data["day_of_week"], defaults=wh_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Добавлено рабочее время для {wh.get_day_of_week_display()}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "База данных успешно заполнена услугами и рабочим временем"
            )
        )
