from datetime import datetime, timedelta
import os
from PIL import Image  # type: ignore
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.text import slugify


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
    photo = models.ImageField(upload_to="car_models/from_users/", blank=True, null=True)

    def __str__(self):
        return f"{self.model} ({self.license_plate})"

    class Meta:
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"

    def _build_default_model_photo_candidates(self):
        """Return candidate relative paths under STATIC for default model images.
        Tries numerous brand/model naming variants inside 'core/car_models/'.
        """
        if not self.model:
            return []
        brand_name = str(self.model.brand.name)
        model_name = str(self.model.name)

        brand_variants = {
            brand_name,
            brand_name.lower(),
            brand_name.upper(),
            slugify(brand_name),
            brand_name.title(),
        }

        model_compact = "".join(ch for ch in model_name if ch.isalnum())
        model_variants = {
            model_name,
            model_name.lower(),
            model_name.upper(),
            model_name.title(),
            slugify(model_name),
        }
        if model_compact:
            model_variants.update(
                {model_compact, model_compact.lower(), model_compact.upper()}
            )

        bases = set()
        for b in brand_variants:
            for m in model_variants:
                bases.add(f"{b}/{m}")
                bases.add(f"{b}_{m}")

        for m in model_variants:
            bases.add(m)

        candidates = []
        for base in bases:
            for ext in (".jpg", ".jpeg", ".png"):
                candidates.append(os.path.join("core", "car_models", base + ext))
        return candidates

    def get_photo_url(self):
        """Return URL to the car's photo or a suitable default from STATIC based on brand/model.
        Fallback order:
        1) Uploaded user photo (media)
        2) Static brand/model image under core/car_models/
        3) Static placeholder (jpg/png/svg)
        """
        try:
            if self.photo and hasattr(self.photo, "url"):
                return self.photo.url
        except Exception:
            pass

        for rel_path in self._build_default_model_photo_candidates():
            if finders.find(rel_path):
                return static(rel_path.replace("\\", "/"))

        for p in (
            "core/img/car-placeholder.jpg",
            "core/img/car-placeholder.png",
            "core/img/car-placeholder.svg",
        ):
            if finders.find(p):
                return static(p)
        return static("core/img/car-placeholder.jpg")


class ServiceCenter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    opening_hours = models.TextField()
    photo = models.ImageField(
        upload_to="service_centers/",
        blank=True,
        null=True,
        default="service_centers/default_service_center.jpg",
    )

    def __str__(self):
        return self.address

    def save(self, *args, **kwargs):
        """Автоматическое сжатие изображения при сохранении"""
        super().save(*args, **kwargs)

        if self.photo and hasattr(self.photo, "path"):
            try:
                img = Image.open(self.photo.path)

                max_size = (1200, 1200)
                if img.height > max_size[1] or img.width > max_size[0]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)

                    if img.mode in ("RGBA", "P", "LA"):
                        rgb_img = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        rgb_img.paste(
                            img,
                            mask=(
                                img.split()[-1] if img.mode in ("RGBA", "LA") else None
                            ),
                        )
                        img = rgb_img

                    img.save(self.photo.path, "JPEG", quality=85, optimize=True)
            except Exception as e:
                pass

    def get_photo_url(self):
        """Return a safe URL to the photo or a static default if missing.
        If media file exists (and is not the legacy default name) return it; otherwise use static default image.
        """
        try:
            default_name = "service_centers/default_service_center.jpg"
            if self.photo and getattr(self.photo, "name", None):
                storage = getattr(self.photo, "storage", None)
                if str(self.photo.name) != default_name and storage:
                    try:
                        if storage.exists(self.photo.name):
                            return self.photo.url
                    except Exception:
                        pass
                basename = os.path.basename(str(self.photo.name))
                if basename:
                    for rel in (
                        f"core/img/service_centers/{basename}",
                        f"core/img/{basename}",
                    ):
                        if finders.find(rel):
                            return static(rel)
        except Exception:
            pass

        return static("core/img/default_service_center.jpg")


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
        return f"{self.user.get_full_name()} ({self.get_position_display()})"  # type: ignore[attr-defined]


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
    service_center = models.ForeignKey(
        ServiceCenter,
        on_delete=models.CASCADE,
        verbose_name="Автосервис",
        related_name="services",
        null=True,
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    def __str__(self):
        return f"{self.name} - {self.service_center}"

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
    service_center = models.ForeignKey(
        ServiceCenter, on_delete=models.CASCADE, verbose_name="Автосервис", null=True
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
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Оплаченная сумма",
        help_text="Фактическая сумма с учетом скидок и использованных бонусов",
    )

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

    def get_base_price(self):
        """Получить базовую цену услуги"""
        from decimal import Decimal

        return Decimal(str(self.service_type.price))

    def get_final_price(self):
        """Получить фактически оплаченную сумму или базовую цену"""
        if self.paid_amount is not None:
            return self.paid_amount
        return self.get_base_price()

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

    service_center = models.ForeignKey(
        ServiceCenter,
        on_delete=models.CASCADE,
        related_name="working_hours",
        verbose_name="Автосервис",
        null=True,
        blank=True,
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK, verbose_name="День недели")
    start_time = models.TimeField(verbose_name="Время начала работы")
    end_time = models.TimeField(verbose_name="Время окончания работы")
    lunch_start = models.TimeField(blank=True, null=True, verbose_name="Начало обеда")
    lunch_end = models.TimeField(blank=True, null=True, verbose_name="Окончание обеда")
    is_working = models.BooleanField(default=True, verbose_name="Рабочий день")

    def __str__(self):
        return f"{self.get_day_of_week_display()}: {self.start_time} - {self.end_time}"  # type: ignore[attr-defined]

    class Meta:
        verbose_name = "Рабочее время"
        verbose_name_plural = "Рабочее время"
        unique_together = ("service_center", "day_of_week")


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_center = models.ForeignKey(
        ServiceCenter, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    admin_reply = models.TextField(blank=True, null=True)
    admin_reply_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("service_center", "user")
        ordering = ["-created_at"]
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self) -> str:
        return f"{self.service_center} — {self.user} ({self.rating})"


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


class BlockedTimeSlot(models.Model):
    """Модель для блокировки временных слотов администратором"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_center = models.ForeignKey(
        ServiceCenter,
        on_delete=models.CASCADE,
        related_name="blocked_slots",
        verbose_name="Автосервис",
    )
    date = models.DateField(verbose_name="Дата")
    time = models.TimeField(verbose_name="Время")
    blocked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Заблокировал",
    )
    blocked_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата блокировки")
    reason = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Причина блокировки"
    )

    class Meta:
        verbose_name = "Заблокированный слот"
        verbose_name_plural = "Заблокированные слоты"
        unique_together = ("service_center", "date", "time")
        ordering = ["date", "time"]

    def __str__(self):
        return f"{self.service_center} - {self.date} {self.time}"
