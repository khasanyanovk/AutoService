import uuid
from django.db import models


class Payment(models.Model):
    """Модель для хранения информации о платежах через ЮKassa"""

    STATUS_CHOICES = [
        ("pending", "Ожидает оплаты"),
        ("waiting_for_capture", "Ожидает подтверждения"),
        ("succeeded", "Оплачено"),
        ("canceled", "Отменено"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        "core.Appointment",
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Запись",
    )
    payment_id = models.CharField(
        max_length=100, unique=True, verbose_name="ID платежа в ЮKassa"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="pending", verbose_name="Статус"
    )
    description = models.CharField(max_length=255, blank=True, verbose_name="Описание")
    confirmation_url = models.URLField(
        max_length=500, blank=True, null=True, verbose_name="Ссылка на оплату"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Оплачен")

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Платеж {self.payment_id} - {self.get_status_display()}"
