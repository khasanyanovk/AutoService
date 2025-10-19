from django.core.management.base import BaseCommand
from core.models import ServiceCenter, ServiceType, WorkingHours
from datetime import time


class Command(BaseCommand):
    help = "Заполняет базу дефолтными сервис-центрами, рабочими часами (с обедом) и услугами"

    def handle(self, *args, **options):
        self.stdout.write("Начало заполнения базы данных...")

        service_centers_data = [
            {
                "address": "ул. Ленина, 123, Москва",
                "phone": "+7 (495) 123-45-67",
                "opening_hours": "09:00-18:00 (Пн-Пт), 10:00-16:00 (Сб)",
                "photo": "service_centers/default_service_center.jpg",
            },
            {
                "address": "пр. Мира, 45, Санкт-Петербург",
                "phone": "+7 (812) 987-65-43",
                "opening_hours": "08:00-19:00 (Пн-Сб)",
                "photo": "service_centers/default_service_center.jpg",
            },
            {
                "address": "ул. Гагарина, 78, Казань",
                "phone": "+7 (843) 555-12-34",
                "opening_hours": "09:00-17:00 (Пн-Пт)",
                "photo": "service_centers/default_service_center.jpg",
            },
            {
                "address": "ул. Советская, 56, Новосибирск",
                "phone": "+7 (383) 444-55-66",
                "opening_hours": "08:00-20:00 (Пн-Вс)",
                "photo": "service_centers/default_service_center.jpg",
            },
            {
                "address": "пр. Победы, 89, Екатеринбург",
                "phone": "+7 (343) 777-88-99",
                "opening_hours": "09:00-19:00 (Пн-Сб)",
                "photo": "service_centers/default_service_center.jpg",
            },
        ]

        created_centers = []
        for center_data in service_centers_data:
            center, created = ServiceCenter.objects.get_or_create(
                address=center_data["address"],
                defaults={
                    "phone": center_data["phone"],
                    "opening_hours": center_data["opening_hours"],
                    "photo": center_data.get(
                        "photo", "service_centers/default_service_center.jpg"
                    ),
                },
            )
            if created:
                created_centers.append(center)
                self.stdout.write(
                    self.style.SUCCESS(f"Создан сервис-центр: {center.address}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Сервис-центр уже существует: {center.address}")
                )

        default_working_hours = [
            (1, time(9, 0), time(18, 0), True),  # Пн
            (2, time(9, 0), time(18, 0), True),  # Вт
            (3, time(9, 0), time(18, 0), True),  # Ср
            (4, time(9, 0), time(18, 0), True),  # Чт
            (5, time(9, 0), time(18, 0), True),  # Пт
            (6, time(10, 0), time(16, 0), True),  # Сб (короче)
            (7, time(0, 0), time(0, 0), False),  # Вс (выходной)
        ]

        def default_lunch_for(day: int, is_working: bool):
            """Возвращает (lunch_start, lunch_end) по умолчанию для дня недели.
            Для будней — 13:00-14:00, для субботы — 13:00-13:30, для выходного — None.
            """
            if not is_working:
                return None, None
            if day in (1, 2, 3, 4, 5):
                return time(13, 0), time(14, 0)
            if day == 6:
                return time(13, 0), time(13, 30)
            return None, None

        wh_created_total = 0
        for center in ServiceCenter.objects.all():
            for day, start, end, is_working in default_working_hours:
                lunch_start, lunch_end = default_lunch_for(day, is_working)
                wh, created = WorkingHours.objects.get_or_create(
                    service_center=center,
                    day_of_week=day,
                    defaults={
                        "start_time": start,
                        "end_time": end,
                        "is_working": is_working,
                        "lunch_start": lunch_start,
                        "lunch_end": lunch_end,
                    },
                )
                if created:
                    wh_created_total += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[{center.address}] добавлен график для дня {day}"
                        )
                    )

        services_data = [
            {
                "name": "Замена моторного масла",
                "description": "Полная замена моторного масла и масляного фильтра. Включает диагностику состояния масла.",
                "duration": 60,
                "price": 2500,
            },
            {
                "name": "Диагностика ходовой части",
                "description": "Комплексная диагностика подвески, амортизаторов, шаровых опор и рулевого управления.",
                "duration": 90,
                "price": 1800,
            },
            {
                "name": "Замена тормозных колодок",
                "description": "Замена передних и задних тормозных колодок. Проверка состояния тормозных дисков.",
                "duration": 120,
                "price": 3500,
            },
            {
                "name": "Развал-схождение",
                "description": "Регулировка углов установки колес на компьютерном стенде. Балансировка колес.",
                "duration": 60,
                "price": 2200,
            },
            {
                "name": "Замена свечей зажигания",
                "description": "Замена комплекта свечей зажигания. Проверка высоковольтных проводов.",
                "duration": 45,
                "price": 1500,
            },
            {
                "name": "Компьютерная диагностика",
                "description": "Полная компьютерная диагностика электронных систем автомобиля.",
                "duration": 30,
                "price": 1200,
            },
            {
                "name": "Замена воздушного фильтра",
                "description": "Замена воздушного фильтра двигателя. Проверка системы впуска.",
                "duration": 20,
                "price": 800,
            },
            {
                "name": "Замена топливного фильтра",
                "description": "Замена топливного фильтра. Проверка давления в топливной системе.",
                "duration": 40,
                "price": 1300,
            },
            {
                "name": "Шиномонтаж",
                "description": "Сезонная замена шин. Балансировка колес. Хранение шин.",
                "duration": 90,
                "price": 2000,
            },
            {
                "name": "Полное техобслуживание",
                "description": "Комплексное техническое обслуживание: замена всех жидкостей и фильтров.",
                "duration": 180,
                "price": 8500,
            },
        ]

        total_services_created = 0
        for center in ServiceCenter.objects.all():
            for service_data in services_data:
                price_variation = service_data["price"] * (
                    0.9 + 0.2 * (hash(center.address) % 10) / 10
                )

                service, created = ServiceType.objects.get_or_create(
                    name=service_data["name"],
                    service_center=center,
                    defaults={
                        "description": service_data["description"],
                        "duration": service_data["duration"],
                        "price": round(price_variation, -2),
                        "is_active": True,
                    },
                )
                if created:
                    total_services_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Создана услуга: {service.name} в {center.address}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Успешно создано {len(created_centers)} сервис-центров, {wh_created_total} записей рабочего времени и {total_services_created} услуг!"
            )
        )

        try:
            from core.models import CarBrand, CarModel

            brands_models = {
                "Toyota": ["Corolla", "Camry", "RAV4"],
                "BMW": ["3 Series", "5 Series", "X5"],
                "Audi": ["A4", "A6", "Q5"],
                "Lada": ["Vesta", "Granta"],
                "Hyundai": ["Solaris", "Tucson"],
            }

            created_brands = 0
            created_models = 0
            for brand_name, model_list in brands_models.items():
                brand, b_created = CarBrand.objects.get_or_create(name=brand_name)
                if b_created:
                    created_brands += 1
                for model_name in model_list:
                    _, m_created = CarModel.objects.get_or_create(
                        brand=brand, name=model_name
                    )
                    if m_created:
                        created_models += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Добавлено марок: {created_brands}, моделей: {created_models}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Блок брендов/моделей пропущен: {e}"))
