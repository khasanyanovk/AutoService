# -*- coding: utf-8 -*-
"""
Тесты производительности (Тест 5)
Проверяют работу системы под нагрузкой
"""
import time
import threading
from decimal import Decimal
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, time as dt_time

from core.models import (
    ServiceCenter,
    ServiceType,
    Car,
    CarBrand,
    CarModel,
    Appointment,
    UserProfile,
)
from loyalty_program.models import LoyaltyAccount


class ConcurrentUsersTestCase(TransactionTestCase):
    """
    Тест 5, Свойство A: одновременная работа нескольких пользователей
    """

    def setUp(self):

        self.brand = CarBrand.objects.create(name="Toyota")
        self.model = CarModel.objects.create(brand=self.brand, name="Camry")

        self.service_center = ServiceCenter.objects.create(
            address="ул. Тестовая, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )

        self.service_type = ServiceType.objects.create(
            name="Замена масла", price=Decimal("2000.00"), duration=60
        )

        self.users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"user{i}", email=f"user{i}@test.com", password="testpass123"
            )
            profile = user.userprofile  # type: ignore
            profile.phone = f"+7999123{i:04d}"
            profile.save()

            Car.objects.create(
                model=self.model, year=2020, license_plate=f"A{i}23BC777", owner=user
            )

            self.users.append(user)

    def test_concurrent_logins(self):
        """5 пользователей логинятся одновременно"""
        results = []

        def login_user(username):
            client = Client()
            start_time = time.time()

            response = client.post(
                reverse("login"), {"username": username, "password": "testpass123"}
            )

            login_time = time.time() - start_time
            results.append(
                {
                    "username": username,
                    "time": login_time,
                    "status": response.status_code,
                }
            )

        threads = []
        for user in self.users:
            thread = threading.Thread(target=login_user, args=(user.username,))
            threads.append(thread)

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        self.assertEqual(len(results), 5, "Не все пользователи залогинились")

        for result in results:
            self.assertIn(
                result["status"],
                [200, 302],
                f"Логин пользователя {result['username']} не прошел",
            )

        self.assertLess(
            total_time,
            10.0,
            f"Одновременный логин 5 пользователей занял {total_time:.2f}с",
        )

        avg_time = sum(r["time"] for r in results) / len(results)
        self.assertLess(
            avg_time, 3.0, f"Среднее время логина {avg_time:.2f}с превышает 3 секунды"
        )

    def test_concurrent_profile_access(self):
        """10 пользователей одновременно обращаются к профилям"""
        results = []

        def access_profile(username):
            client = Client()
            client.login(username=username, password="testpass123")

            start_time = time.time()
            response = client.get(reverse("profile"))
            access_time = time.time() - start_time

            results.append(
                {
                    "username": username,
                    "time": access_time,
                    "status": response.status_code,
                }
            )

        threads = []
        for user in self.users:
            thread = threading.Thread(target=access_profile, args=(user.username,))
            threads.append(thread)

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        self.assertGreater(len(results), 0, "Results should not be empty")

        for result in results:
            self.assertEqual(
                result["status"],
                200,
                f"Доступ к профилю {result['username']} не удался",
            )

        if results:
            max_time = max(r["time"] for r in results)
            self.assertLess(
                max_time, 5.0, f"Самый медленный запрос занял {max_time:.2f}с"
            )


class DatabaseQueryPerformanceTestCase(TestCase):
    """
    Тест 5, Свойство B: производительность запросов к БД
    """

    def setUp(self):
        brand = CarBrand.objects.create(name="Toyota")
        model = CarModel.objects.create(brand=brand, name="Camry")

        self.service_center = ServiceCenter.objects.create(
            address="ул. Тестовая, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )

        self.service_type = ServiceType.objects.create(
            name="Замена масла", price=Decimal("2000.00"), duration=60
        )

        for i in range(50):
            user = User.objects.create_user(
                username=f"user{i}", email=f"user{i}@test.com", password="testpass123"
            )
            profile = user.userprofile  # type: ignore
            profile.phone = f"+7999123{i:04d}"
            profile.save()

            car = Car.objects.create(
                model=model, year=2020, license_plate=f"A{i:03d}BC777", owner=user
            )

            for j in range(3):
                Appointment.objects.create(
                    car=car,
                    service_type=self.service_type,
                    service_center=self.service_center,
                    scheduled_date=timezone.now().date() + timedelta(days=j),
                    scheduled_time=dt_time(10, 0),
                    status="SCHEDULED",
                )

    def test_appointment_list_query_performance(self):
        """Список заказов загружается быстро даже с большим количеством записей"""
        user = User.objects.first()
        client = Client()
        client.force_login(user)  # type: ignore

        start_time = time.time()
        response = client.get(reverse("profile"))
        query_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(
            query_time, 3.0, f"Загрузка списка заказов заняла {query_time:.2f}с"
        )

    def test_search_performance_with_many_records(self):
        """Поиск работает быстро даже с большим количеством записей"""
        from django.contrib.auth.models import Group

        manager = User.objects.create_user(
            username="manager", email="manager@test.com", password="managerpass123"
        )
        manager_group, _ = Group.objects.get_or_create(name="Managers")
        manager.groups.add(manager_group)
        manager.is_staff = True
        manager.save()

        client = Client()
        client.force_login(manager)

        start_time = time.time()
        response = client.get(reverse("admin_panel:admin_users"), {"search": "user25"})
        search_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(search_time, 2.0, f"Поиск занял {search_time:.2f}с")


class PageLoadPerformanceTestCase(TestCase):
    """
    Тест 5, Свойство C: производительность загрузки страниц
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        profile = self.user.userprofile  # type: ignore
        profile.phone = "+79991234567"
        profile.save()

    def test_home_page_load_time(self):
        """Главная страница загружается быстро"""
        start_time = time.time()
        response = self.client.get("/")
        load_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(
            load_time, 2.0, f"Главная страница загрузилась за {load_time:.2f}с"
        )

    def test_service_list_load_time(self):
        """Список услуг загружается быстро"""
        for i in range(20):
            ServiceType.objects.create(
                name=f"Услуга {i}",
                price=Decimal("1000.00") + Decimal(i * 100),
                duration=60,
            )

        start_time = time.time()

        response = self.client.get(reverse("home"))
        load_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(load_time, 2.0, f"Список услуг загрузился за {load_time:.2f}с")

    def test_profile_load_with_history(self):
        """Профиль с историей заказов загружается быстро"""
        self.client.login(username="testuser", password="testpass123")

        brand = CarBrand.objects.create(name="Toyota")
        model = CarModel.objects.create(brand=brand, name="Camry")
        car = Car.objects.create(
            model=model, year=2020, license_plate="A123BC777", owner=self.user
        )

        service_center = ServiceCenter.objects.create(
            address="ул. Тестовая, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )

        service_type = ServiceType.objects.create(
            name="Замена масла", price=Decimal("2000.00"), duration=60
        )

        for i in range(10):
            Appointment.objects.create(
                car=car,
                service_type=service_type,
                service_center=service_center,
                scheduled_date=timezone.now().date() - timedelta(days=i),
                scheduled_time=dt_time(10, 0),
                status="COMPLETED",
            )

        start_time = time.time()
        response = self.client.get(reverse("profile"))
        load_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(
            load_time, 3.0, f"Профиль с историей загрузился за {load_time:.2f}с"
        )


class StressTestCase(TransactionTestCase):
    """
    Тест 5, Свойство D: стресс-тестирование
    """

    def setUp(self):
        self.brand = CarBrand.objects.create(name="Toyota")
        self.model = CarModel.objects.create(brand=self.brand, name="Camry")

        self.service_center = ServiceCenter.objects.create(
            address="ул. Тестовая, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )

        self.service_type = ServiceType.objects.create(
            name="Замена масла", price=Decimal("2000.00"), duration=60
        )

    def test_rapid_appointment_creation(self):
        """Быстрое создание множества заказов"""
        user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        profile = user.userprofile  # type: ignore
        profile.phone = "+79991234567"
        profile.save()

        car = Car.objects.create(
            model=self.model, year=2020, license_plate="A123BC777", owner=user
        )

        start_time = time.time()

        appointments_created = 0
        for i in range(20):
            try:
                Appointment.objects.create(
                    car=car,
                    service_type=self.service_type,
                    service_center=self.service_center,
                    scheduled_date=timezone.now().date() + timedelta(days=i),
                    scheduled_time=dt_time(10, 0),
                    status="SCHEDULED",
                )
                appointments_created += 1
            except Exception as e:
                print(f"Ошибка при создании заказа {i}: {e}")

        creation_time = time.time() - start_time

        self.assertEqual(appointments_created, 20, "Не все заказы были созданы")

        self.assertLess(
            creation_time, 10.0, f"Создание 20 заказов заняло {creation_time:.2f}с"
        )

        saved_appointments = Appointment.objects.filter(car=car).count()
        self.assertEqual(saved_appointments, 20)
