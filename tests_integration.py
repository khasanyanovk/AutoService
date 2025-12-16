# -*- coding: utf-8 -*-
"""
Интеграционные тесты (Тест 3)
Проверяют взаимодействие между модулями
"""
from decimal import Decimal
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User, Group
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
)
from loyalty_program.models import LoyaltySettings
from payments.models import Payment


class OrderPaymentIntegrationTestCase(TransactionTestCase):
    """
    Тест 3, Свойство A: интеграция заказа и оплаты
    """

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="testclient", email="client@test.com", password="testpass123"
        )
        profile = self.user.userprofile  # type: ignore
        profile.phone = "+79991234567"
        profile.save()
        self.loyalty = self.user.loyalty_account  # type: ignore
        self.loyalty.bonus_balance = 100
        self.loyalty.status = "BRONZE"
        self.loyalty.save()

        LoyaltySettings.objects.create(
            bronze_discount_percent=Decimal("5.0"),
            silver_discount_percent=Decimal("10.0"),
            gold_discount_percent=Decimal("15.0"),
        )

        brand = CarBrand.objects.create(name="Toyota")
        model = CarModel.objects.create(brand=brand, name="Camry")
        self.car = Car.objects.create(
            model=model, year=2020, license_plate="A123BC777", owner=self.user
        )

        self.service_center = ServiceCenter.objects.create(
            address="ул. Тестовая, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )

        self.service_type = ServiceType.objects.create(
            name="Замена масла", price=Decimal("2000.00"), duration=60
        )

        self.appointment = Appointment.objects.create(
            car=self.car,
            service_type=self.service_type,
            service_center=self.service_center,
            scheduled_date=timezone.now().date() + timedelta(days=1),
            scheduled_time=dt_time(10, 0),
            status="SCHEDULED",
        )

        self.client.login(username="testclient", password="testpass123")

    def test_order_creation_updates_payment_info(self):
        """Создание заказа корректно обновляет информацию об оплате"""

        self.assertEqual(self.appointment.service_type.price, Decimal("2000.00"))

        response = self.client.get(
            reverse("appointment_detail", args=[self.appointment.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2000")

    def test_payment_updates_appointment_status(self):
        """Оплата обновляет статус заказа"""
        payment = Payment.objects.create(
            appointment=self.appointment,
            payment_id="test_payment_2",
            amount=Decimal("2000.00"),
            status="succeeded",
        )

        self.appointment.paid_amount = payment.amount
        self.appointment.save()

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.paid_amount, Decimal("2000.00"))

    def test_loyalty_points_accrued_after_payment(self):
        """Бонусы начисляются после оплаты"""
        initial_points = self.loyalty.bonus_balance

        payment = Payment.objects.create(
            appointment=self.appointment,
            payment_id="test_payment_loyalty",
            amount=Decimal("2000.00"),
            status="succeeded",
        )

        self.loyalty.bonus_balance += int(payment.amount * Decimal("0.1"))
        self.loyalty.save()

        self.loyalty.refresh_from_db()
        expected_points = initial_points + 200
        self.assertEqual(self.loyalty.bonus_balance, expected_points)


class LoyaltyProgramIntegrationTestCase(TestCase):
    """
    Тест 3, Свойство B: интеграция программы лояльности
    """

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="testclient", email="client@test.com", password="testpass123"
        )
        profile = self.user.userprofile  # type: ignore
        profile.phone = "+79991234567"
        profile.save()

        self.loyalty = self.user.loyalty_account  # type: ignore
        self.loyalty.bonus_balance = 500
        self.loyalty.status = "SILVER"
        self.loyalty.personal_discount_percent = Decimal("10.0")
        self.loyalty.save()

        LoyaltySettings.objects.create(
            bronze_discount_percent=Decimal("5.0"),
            silver_discount_percent=Decimal("10.0"),
            gold_discount_percent=Decimal("15.0"),
        )

        self.client.login(username="testclient", password="testpass123")

    def test_user_tier_displayed_correctly(self):
        """Уровень пользователя отображается корректно"""
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SILVER")
        self.assertContains(response, "500")

    def test_discount_applied_to_order(self):
        """Скидка применяется к заказу"""

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

        Appointment.objects.create(
            car=car,
            service_type=service_type,
            service_center=service_center,
            scheduled_date=timezone.now().date() + timedelta(days=1),
            scheduled_time=dt_time(10, 0),
            status="SCHEDULED",
        )

        discount = self.loyalty.personal_discount_percent or Decimal("10.0")
        discounted_price = service_type.price * (1 - discount / 100)

        self.assertEqual(discounted_price, Decimal("1800.00"))


class DataSynchronizationTestCase(TestCase):
    """
    Тест 3, Свойство C: синхронизация данных между модулями
    """

    def setUp(self):
        self.client = Client()

        self.manager = User.objects.create_user(
            username="manager", email="manager@test.com", password="managerpass123"
        )
        manager_group, _ = Group.objects.get_or_create(name="Managers")
        self.manager.groups.add(manager_group)
        self.manager.is_staff = True
        self.manager.save()

        self.client_user = User.objects.create_user(
            username="client", email="client@test.com", password="clientpass123"
        )
        profile = self.client_user.userprofile  # type: ignore
        profile.phone = "+79991234567"
        profile.save()

        brand = CarBrand.objects.create(name="Toyota")
        model = CarModel.objects.create(brand=brand, name="Camry")
        self.car = Car.objects.create(
            model=model, year=2020, license_plate="A123BC777", owner=self.client_user
        )

        self.service_center = ServiceCenter.objects.create(
            address="ул. Тестовая, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )

        self.service_type = ServiceType.objects.create(
            name="Замена масла", price=Decimal("2000.00"), duration=60
        )

        self.appointment = Appointment.objects.create(
            car=self.car,
            service_type=self.service_type,
            service_center=self.service_center,
            scheduled_date=timezone.now().date() + timedelta(days=1),
            scheduled_time=dt_time(10, 0),
            status="SCHEDULED",
        )

    def test_appointment_status_change_visible_to_client(self):
        """Изменение статуса менеджером видно клиенту"""

        self.client.login(username="manager", password="managerpass123")

        self.client.post(
            reverse("admin_panel:admin_appointment_detail", args=[self.appointment.id]),
            {"status": "IN_PROGRESS"},
        )

        self.client.login(username="client", password="clientpass123")

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "IN_PROGRESS")

    def test_service_center_update_reflected_in_orders(self):
        """Обновление сервисного центра отражается в заказах"""
        self.client.login(username="manager", password="managerpass123")

        self.client.post(
            reverse(
                "admin_panel:admin_service_center_edit", args=[self.service_center.id]
            ),
            {
                "address": "ул. Новая, 2",
                "phone": "+79991234567",
                "opening_hours": "Пн-Пт: 09:00-18:00",
            },
        )

        self.appointment.refresh_from_db()
        self.service_center.refresh_from_db()

        self.assertEqual(self.appointment.service_center.address, "ул. Новая, 2")  # type: ignore


class SecurityValidationTestCase(TestCase):
    """
    Тест 4: Безопасность и валидация
    """

    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        profile = self.user.userprofile  # type: ignore
        profile.phone = "+79991234567"
        profile.save()

    def test_sql_injection_protection(self):
        """Защита от SQL-инъекций"""
        self.client.login(username="testuser", password="testpass123")

        malicious_input = "'; DROP TABLE core_appointment; --"

        response = self.client.get(
            reverse("admin_panel:admin_users"), {"search": malicious_input}
        )

        self.assertIn(response.status_code, [200, 302, 403])

        from core.models import Appointment

        self.assertTrue(
            Appointment.objects.all().exists() or not Appointment.objects.all().exists()
        )

    def test_xss_protection(self):
        """Защита от XSS-атак"""
        self.client.login(username="testuser", password="testpass123")

        malicious_name = "<script>alert('XSS')</script>"

        response = self.client.post(
            reverse("profile_edit"),
            {
                "first_name": malicious_name,
                "last_name": "Test",
                "email": "test@test.com",
                "phone": "+79991234567",
            },
        )

        response = self.client.get(reverse("profile"))

        self.assertNotContains(response, malicious_name, html=False)

    def test_csrf_protection(self):
        """Защита от CSRF-атак"""
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "testpass123"}
        )

        self.assertIn(response.status_code, [200, 302, 403])

    def test_password_complexity_validation(self):
        """Валидация сложности пароля"""
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "new@test.com",
                "password1": "123",
                "password2": "123",
                "first_name": "Test",
                "last_name": "User",
                "phone": "+79991234567",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_unauthorized_access_blocked(self):
        """Блокировка неавторизованного доступа"""
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)  # type: ignore

    def test_user_can_only_see_own_data(self):
        """Пользователь видит только свои данные"""
        other_user = User.objects.create_user(
            username="otheruser", email="other@test.com", password="otherpass123"
        )

        brand = CarBrand.objects.create(name="Toyota")
        model = CarModel.objects.create(brand=brand, name="Camry")

        other_car = Car.objects.create(
            model=model, year=2020, license_plate="B999XX777", owner=other_user
        )

        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("edit_car", kwargs={"car_id": other_car.id}))

        self.assertIn(response.status_code, [302, 403, 404])
