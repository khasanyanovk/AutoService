"""
Тесты для модуля менеджера (Тест 2)
"""

import time
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from core.models import (
    CarBrand,
    CarModel,
    Car,
    ServiceCenter,
    ServiceType,
    Appointment,
    UserProfile,
)
from loyalty_program.models import LoyaltyAccount


class ManagerAccessControlTestCase(TestCase):
    """
    Тест 2, Свойство A: контроль доступа
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="manager", email="manager@test.com", password="managerpass123"
        )
        self.manager.is_staff = True
        self.manager.save()

        self.client_user = User.objects.create_user(
            username="client", email="client@test.com", password="clientpass123"
        )

        profile = self.client_user.userprofile
        profile.phone = "+79991234567"
        profile.save()

        brand = CarBrand.objects.create(name="Toyota")
        model = CarModel.objects.create(brand=brand, name="Camry")
        self.car = Car.objects.create(
            model=model, year=2020, license_plate="A123BC777", owner=self.client_user
        )

        self.service_center = ServiceCenter.objects.create(
            address="ул. Ленина, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )
        self.service_type = ServiceType.objects.create(
            name="Замена масла", price=1500.0, duration=60
        )

    def test_manager_can_access_admin_panel(self):
        """Менеджер может получить доступ к админ-панели"""
        self.client.login(username="manager", password="managerpass123")

        response = self.client.get(reverse("admin_panel:admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Панель администратора")

    def test_unauthenticated_user_cannot_access_admin_panel(self):
        """Неаутентифицированный пользователь не может получить доступ"""
        response = self.client.get(reverse("admin_panel:admin_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)  # type: ignore

    def test_regular_user_cannot_access_admin_panel(self):
        """Обычный клиент не может получить доступ к админ-панели"""
        self.client.login(username="client", password="clientpass123")

        response = self.client.get(reverse("admin_panel:admin_dashboard"))

        self.assertNotEqual(response.status_code, 200)


class ManagerOrderStatusTestCase(TestCase):
    """
    Тест 2, Свойство B: управление статусами заказов
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="manager", email="manager@test.com", password="managerpass123"
        )
        self.manager.is_staff = True
        self.manager.save()

        client_user = User.objects.create_user(
            username="client", email="client@test.com", password="clientpass123"
        )

        profile = client_user.userprofile
        profile.phone = "+79991234567"
        profile.save()

        brand = CarBrand.objects.create(name="Toyota")
        model = CarModel.objects.create(brand=brand, name="Camry")
        car = Car.objects.create(
            model=model, year=2020, license_plate="A123BC777", owner=client_user
        )

        service_center = ServiceCenter.objects.create(
            address="ул. Ленина, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )
        service_type = ServiceType.objects.create(
            name="Замена масла", price=1500.0, duration=60
        )

        from datetime import date, time as dt_time

        self.appointment = Appointment.objects.create(
            car=car,
            service_center=service_center,
            service_type=service_type,
            scheduled_date=date(2025, 12, 20),
            scheduled_time=dt_time(10, 0),
            status="SCHEDULED",
        )

        self.client.login(username="manager", password="managerpass123")

    def test_manager_can_see_all_statuses(self):
        """Менеджер видит все доступные статусы"""
        response = self.client.get(
            reverse("admin_panel:admin_appointment_detail", args=[self.appointment.id])
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Запланировано")

    def test_status_change_updates_correctly(self):
        """Статус корректно обновляется"""
        response = self.client.post(
            reverse("admin_panel:admin_appointment_detail", args=[self.appointment.id]),
            {"status": "IN_PROGRESS"},
        )

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "IN_PROGRESS")

    def test_manager_can_change_order_status_quickly(self):
        """Менеджер может изменить статус заказа за < 1 секунды"""
        start_time = time.time()

        self.client.post(
            reverse("admin_panel:admin_appointment_detail", args=[self.appointment.id]),
            {"status": "completed"},
        )

        update_time = time.time() - start_time

        self.assertLess(update_time, 1.0, "Обновление статуса превышает 1 секунду")


class ManagerScheduleTestCase(TestCase):
    """
    Тест 2, Свойство C: работа с расписанием
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="manager", email="manager@test.com", password="managerpass123"
        )
        self.manager.is_staff = True
        self.manager.save()

        self.service_center = ServiceCenter.objects.create(
            address="ул. Ленина, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )

        self.client.login(username="manager", password="managerpass123")

    def test_schedule_loads_within_time_limit(self):
        """Расписание загружается за < 3 секунд"""
        start_time = time.time()

        response = self.client.get(
            reverse(
                "admin_panel:admin_service_center_detail", args=[self.service_center.id]
            )
        )

        load_time = time.time() - start_time

        self.assertLess(load_time, 3.0, "Загрузка расписания превышает 3 секунды")
        self.assertEqual(response.status_code, 200)

    def test_schedule_update_saves_quickly(self):
        """Изменение расписания сохраняется за < 2 секунд"""
        start_time = time.time()

        response = self.client.post(
            reverse(
                "admin_panel:admin_service_center_edit", args=[self.service_center.id]
            ),
            {
                "address": "ул. Новая, 2",
                "phone": "+79991234567",
            },
        )

        save_time = time.time() - start_time

        self.assertLess(save_time, 2.0, "Сохранение расписания превышает 2 секунды")

        self.service_center.refresh_from_db()
        self.assertEqual(self.service_center.address, "ул. Новая, 2")


class ManagerClientSearchTestCase(TestCase):
    """
    Тест 2, Свойство D: поиск клиентов
    """

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username="manager", email="manager@test.com", password="managerpass123"
        )
        self.manager.is_staff = True
        self.manager.save()

        self.client1 = User.objects.create_user(
            username="ivanov",
            email="ivanov@test.com",
            password="pass123",
            first_name="Иван",
            last_name="Иванов",
        )
        profile1 = self.client1.userprofile
        profile1.phone = "+79991111111"
        profile1.save()

        self.client2 = User.objects.create_user(
            username="petrov",
            email="petrov@test.com",
            password="pass123",
            first_name="Петр",
            last_name="Петров",
        )
        profile2 = self.client2.userprofile
        profile2.phone = "+79992222222"
        profile2.save()

        self.client.login(username="manager", password="managerpass123")

    def test_search_by_phone_finds_client(self):
        """Поиск по номеру телефона находит клиента"""
        response = self.client.get(
            reverse("admin_panel:admin_users") + "?search=79991111111"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Иван")

    def test_search_by_name_finds_client(self):
        """Поиск по имени находит клиента"""
        response = self.client.get(reverse("admin_panel:admin_users") + "?search=Петр")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Петр")

    def test_search_returns_results_quickly(self):
        """Поиск возвращает результаты за < 2 секунд"""
        start_time = time.time()

        self.client.get(reverse("admin_panel:admin_users") + "?search=Иван")

        search_time = time.time() - start_time

        self.assertLess(search_time, 2.0, "Поиск превышает 2 секунды")
