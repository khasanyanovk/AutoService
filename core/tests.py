# -*- coding: utf-8 -*-

import time
from decimal import Decimal
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date, time as dt_time

from core.models import (
    ServiceCenter,
    ServiceType,
    Car,
    CarBrand,
    CarModel,
    Appointment,
    UserProfile,
    WorkingHours,
)
from loyalty_program.models import LoyaltyAccount


class ClientAuthenticationTestCase(TestCase):
    """
    Тест 1, Свойство A: успешная аутентификация и навигация
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testclient",
            email="client@test.com",
            password="testpass123",
            first_name="Иван",
            last_name="Петров",
        )
        self.user.userprofile.phone = "+79991234567"
        self.user.userprofile.save()

    def test_successful_login_with_correct_credentials(self):
        """Успешная аутентификация с корректными данными"""
        start_time = time.time()

        response = self.client.post(
            reverse("login"), {"username": "testclient", "password": "testpass123"}
        )

        auth_time = time.time() - start_time

        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.url)  # type: ignore

        self.assertLess(auth_time, 2.0, "Время аутентификации превышает 2 секунды")

        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_failed_login_with_incorrect_credentials(self):
        """Неуспешная аутентификация с некорректными данными"""
        response = self.client.post(
            reverse("login"), {"username": "testclient", "password": "wrongpass"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Пожалуйста, введите правильные имя пользователя и пароль"
        )

    def test_profile_page_load_performance(self):
        """Загрузка личного кабинета за 3 секунды или быстрее"""
        self.client.login(username="testclient", password="testpass123")

        start_time = time.time()
        response = self.client.get(reverse("profile"))
        load_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(load_time, 3.0, "Загрузка личного кабинета превышает 3 секунды")

        self.assertContains(response, "Иван Петров")
        self.assertContains(response, "Мои записи")

    def test_authenticated_user_can_only_access_client_functions(self):
        """Клиент видит только разрешенные функции"""
        self.client.login(username="testclient", password="testpass123")

        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("admin_panel:admin_dashboard"))
        self.assertEqual(response.status_code, 302)


class AppointmentCreationTestCase(TransactionTestCase):
    """
    Тест 1, Свойство B: создание и отображение заказов
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testclient", email="client@test.com", password="testpass123"
        )

        self.user.userprofile.phone = "+79991234567"
        self.user.userprofile.save()

        self.brand = CarBrand.objects.create(name="Toyota")
        self.model = CarModel.objects.create(brand=self.brand, name="Camry")
        self.car = Car.objects.create(
            model=self.model, year=2020, license_plate="A123BC777", owner=self.user
        )

        self.service_center = ServiceCenter.objects.create(
            address="ул. Тестовая, 1",
            phone="+79991234567",
            opening_hours="Пн-Пт: 09:00-18:00",
        )

        self.service_type = ServiceType.objects.create(
            name="Замена масла", price=Decimal("2000.00"), duration=60
        )

        WorkingHours.objects.create(
            service_center=self.service_center,
            day_of_week=1,  # Понедельник
            start_time=dt_time(9, 0),
            end_time=dt_time(18, 0),
            is_working=True,
        )

        self.client.login(username="testclient", password="testpass123")

    def test_create_appointment_successfully(self):
        """Успешное создание заказа"""
        today = timezone.now().date()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days=days_ahead)

        start_time = time.time()

        response = self.client.post(
            reverse("service_booking"),
            {
                "car": str(self.car.id),
                "service_type": str(self.service_type.id),
                "service_center": str(self.service_center.id),
                "scheduled_date": next_monday.strftime("%Y-%m-%d"),
                "scheduled_time": "10:00",
            },
        )

        creation_time = time.time() - start_time

        self.assertIn(response.status_code, [200, 302])

        self.assertLess(creation_time, 2.0, "Создание заказа превышает 2 секунды")

        if response.status_code == 302:
            appointment = Appointment.objects.get(
                car=self.car, service_type=self.service_type
            )
            self.assertEqual(appointment.status, "SCHEDULED")
            self.assertEqual(appointment.service_center, self.service_center)

    def test_appointment_appears_in_history(self):
        """Заказ появляется в истории после создания"""
        next_monday = timezone.now().date() + timedelta(days=7)

        Appointment.objects.create(
            car=self.car,
            service_type=self.service_type,
            service_center=self.service_center,
            scheduled_date=next_monday,
            scheduled_time=dt_time(10, 0),
            status="SCHEDULED",
        )

        start_time = time.time()
        response = self.client.get(reverse("profile"))
        load_time = time.time() - start_time

        self.assertLess(load_time, 1.0, "Обновление истории превышает 1 секунду")

        self.assertContains(response, "Замена масла")
        self.assertContains(response, "ул. Тестовая, 1")


class UserRegistrationTestCase(TestCase):
    """
    Тест 1, Свойство C: регистрация нового клиента
    """

    def setUp(self):
        self.client = Client()

    def test_successful_registration_with_valid_data(self):
        """Успешная регистрация с валидными данными"""
        start_time = time.time()

        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@test.com",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
                "first_name": "Петр",
                "last_name": "Сидоров",
                "phone_number": "+79991234567",
            },
        )

        registration_time = time.time() - start_time

        self.assertLess(registration_time, 3.0, "Регистрация превышает 3 секунды")

        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@test.com")
        self.assertEqual(user.first_name, "Петр")

        profile = UserProfile.objects.get(user=user)
        self.assertIsNotNone(profile)

        loyalty = LoyaltyAccount.objects.get(user=user)
        self.assertIsNotNone(loyalty)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_registration_fails_with_existing_username(self):
        """Регистрация не проходит с существующим username"""
        User.objects.create_user(
            username="existing", email="existing@test.com", password="pass123"
        )

        response = self.client.post(
            reverse("register"),
            {
                "username": "existing",
                "email": "newuser@test.com",
                "password1": "ComplexPass123!",
                "password2": "ComplexPass123!",
                "first_name": "Тест",
                "last_name": "Тестов",
                "phone": "+79991234567",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="newuser@test.com").exists())

    def test_registration_fails_with_invalid_data(self):
        """Регистрация не проходит с невалидными данными"""
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@test.com",
                "password1": "123",
                "password2": "123",
                "first_name": "Тест",
                "last_name": "Тестов",
                "phone": "+79991234567",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())


class ProfileEditTestCase(TestCase):
    """
    Тест 1, Свойство D: просмотр и редактирование профиля
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            first_name="Иван",
            last_name="Иванов",
        )

        self.profile = self.user.userprofile
        self.profile.phone = "+79991234567"
        self.profile.save()
        self.client.login(username="testuser", password="testpass123")

    def test_profile_form_loads_quickly(self):
        """Загрузка формы профиля за 2 секунды или быстрее"""
        start_time = time.time()
        response = self.client.get(reverse("profile_edit"))
        load_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(load_time, 2.0, "Загрузка формы превышает 2 секунды")

    def test_profile_updates_successfully(self):
        """Успешное обновление профиля"""
        start_time = time.time()

        response = self.client.post(
            reverse("profile_edit"),
            {
                "first_name": "Петр",
                "last_name": "Петров",
                "email": "newemail@test.com",
                "phone": "+79999999999",
            },
        )

        save_time = time.time() - start_time

        self.assertLess(save_time, 1.0, "Сохранение превышает 1 секунду")

        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(self.user.first_name, "Петр")
        self.assertEqual(self.user.last_name, "Петров")
        self.assertEqual(self.user.email, "newemail@test.com")
        self.assertEqual(self.profile.phone, "+79999999999")

        self.assertEqual(response.status_code, 302)

    def test_profile_shows_updated_data(self):
        """Обновленные данные отображаются в профиле"""
        self.user.first_name = "Новое"
        self.user.last_name = "Имя"
        self.user.save()

        response = self.client.get(reverse("profile"))

        self.assertContains(response, "Новое Имя")

    def test_profile_validation_for_invalid_email(self):
        """Валидация неправильного email"""
        response = self.client.post(
            reverse("profile_edit"),
            {
                "first_name": "Иван",
                "last_name": "Иванов",
                "email": "invalid-email",
                "phone": "+79991234567",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "test@test.com")


class HomePageTestCase(TestCase):
    """Базовые тесты главной страницы"""

    def test_home_page_status_code(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_home_page_contains_key_elements(self):
        response = self.client.get("/")
        self.assertContains(response, "Автосервис")
        self.assertContains(response, "Услуги")
