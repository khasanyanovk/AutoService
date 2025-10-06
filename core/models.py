from datetime import datetime, timedelta
from PIL import Image
import uuid
from django.db import models
from django.contrib.auth.models import User


class CarBrand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CarModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(CarBrand, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ["brand", "name"]

    def __str__(self):
        return f"{self.brand} {self.name}"


class Car(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year = models.PositiveIntegerField()
    model = models.ForeignKey(CarModel, on_delete=models.CASCADE)
    license_plate = models.CharField(max_length=20, unique=True)
    vin = models.CharField(max_length=17, unique=True, blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.model} ({self.license_plate})"

    class Meta:
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"


class ServiceCenter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    opening_hours = models.TextField()

    def __str__(self):
        return self.address


class Employee(models.Model):
    POSITION_CHOICES = [
        ("MECH", "Mechanic"),
        ("MAN", "Manager"),
        ("DIR", "Director"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    position = models.CharField(max_length=4, choices=POSITION_CHOICES)
    phone = models.CharField(max_length=20)
    hire_date = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_position_display()})"


class Part(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    compatible_models = models.ManyToManyField(CarModel)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    in_stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ("PEND", "Pending"),
        ("DIAG", "Diagnostics"),
        ("WAIT", "Waiting for Parts"),
        ("REPR", "In Repair"),
        ("DONE", "Completed"),
        ("CANC", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default="PEND")
    description = models.TextField()
    assigned_mechanics = models.ManyToManyField(
        Employee, limit_choices_to={"position": "MECH"}
    )

    def __str__(self):
        return f"Request #{self.id} - {self.car}"


class PartOrder(models.Model):
    STATUS_CHOICES = [
        ("ORDE", "Ordered"),
        ("SHIP", "Shipped"),
        ("DELI", "Delivered"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default="ORDE")
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE)

    def __str__(self):
        return f"Order #{self.id} - {self.part.name}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"

    def save(self, *args, **kwargs):
        original_avatar = None
        if self.pk:
            try:
                original = UserProfile.objects.get(pk=self.pk)
                original_avatar = original.avatar
            except UserProfile.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.avatar and (not original_avatar or self.avatar != original_avatar):
            try:
                img = Image.open(self.avatar.path)

                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                if img.width > 150 or img.height > 150:
                    output_size = (150, 150)
                    img.thumbnail(output_size, Image.Resampling.LANCZOS)
                    img.save(self.avatar.path)
            except Exception as e:
                print(f"Ошибка при обработке аватара: {e}")


class ServiceType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Название услуги")
    description = models.TextField(verbose_name="Описание", blank=True)
    duration = models.PositiveIntegerField(
        verbose_name="Продолжительность (минуты)",
        help_text="Продолжительность услуги в минутах",
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Стоимость"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тип услуги"
        verbose_name_plural = "Типы услуг"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("SCHEDULED", "Запланировано"),
        ("IN_PROGRESS", "В работе"),
        ("COMPLETED", "Завершено"),
        ("CANCELLED", "Отменено"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, verbose_name="Автомобиль")
    service_type = models.ForeignKey(
        ServiceType, on_delete=models.CASCADE, verbose_name="Тип услуги"
    )
    scheduled_date = models.DateField(verbose_name="Дата записи")
    scheduled_time = models.TimeField(verbose_name="Время записи")
    end_time = models.TimeField(verbose_name="Время окончания", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="SCHEDULED",
        verbose_name="Статус",
    )
    notes = models.TextField(verbose_name="Примечания", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.scheduled_time and self.service_type:
            start_datetime = datetime.combine(self.scheduled_date, self.scheduled_time)
            end_datetime = start_datetime + timedelta(
                minutes=self.service_type.duration
            )
            self.end_time = end_datetime.time()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.car} - {self.service_type} - {self.scheduled_date} {self.scheduled_time}"

    class Meta:
        verbose_name = "Запись на услугу"
        verbose_name_plural = "Записи на услуги"
        ordering = ["-scheduled_date", "scheduled_time"]


class WorkingHours(models.Model):
    DAYS_OF_WEEK = [
        (1, "Понедельник"),
        (2, "Вторник"),
        (3, "Среда"),
        (4, "Четверг"),
        (5, "Пятница"),
        (6, "Суббота"),
        (7, "Воскресенье"),
    ]

    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK, unique=True, verbose_name="День недели"
    )
    start_time = models.TimeField(verbose_name="Время начала работы")
    end_time = models.TimeField(verbose_name="Время окончания работы")
    is_working = models.BooleanField(default=True, verbose_name="Рабочий день")

    def __str__(self):
        return f"{self.get_day_of_week_display()}: {self.start_time} - {self.end_time}"

    class Meta:
        verbose_name = "Рабочее время"
        verbose_name_plural = "Рабочее время"


class AdminDashboard(models.Model):
    """Модель для хранения настроек админ-панели"""

    service_center = models.OneToOneField(
        ServiceCenter, on_delete=models.CASCADE, verbose_name="Автосервис"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Дашборд для {self.service_center}"

    class Meta:
        verbose_name = "Дашборд администратора"
        verbose_name_plural = "Дашборды администраторов"
