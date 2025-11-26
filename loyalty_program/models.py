import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class LoyaltySettings(models.Model):
    """Глобальные настройки программы лояльности"""

    online_payment_bonus_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="Процент бонусов за онлайн оплату",
        help_text="Процент от стоимости услуги, возвращаемый бонусами при онлайн оплате",
    )

    offline_payment_bonus_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="Процент бонусов за оплату в центре",
        help_text="Процент от стоимости услуги, возвращаемый бонусами при оплате в центре",
    )

    max_bonus_usage_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("70.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="Максимальный % оплаты бонусами",
        help_text="Максимальный процент стоимости услуги, который можно оплатить бонусами",
    )

    bronze_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("20000.00"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Порог для статуса Бронза",
        help_text="Общая сумма покупок для достижения статуса Бронза",
    )

    silver_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("50000.00"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Порог для статуса Серебро",
        help_text="Общая сумма покупок для достижения статуса Серебро",
    )

    gold_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("100000.00"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Порог для статуса Золото",
        help_text="Общая сумма покупок для достижения статуса Золото",
    )

    platinum_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("200000.00"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Порог для статуса Платина",
        help_text="Общая сумма покупок для достижения статуса Платина",
    )

    # Скидки по статусам
    bronze_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("3.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="Скидка для Бронзы",
        help_text="Процент скидки для клиентов со статусом Бронза",
    )

    silver_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("6.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="Скидка для Серебра",
        help_text="Процент скидки для клиентов со статусом Серебро",
    )

    gold_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("12.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="Скидка для Золота",
        help_text="Процент скидки для клиентов со статусом Золото",
    )

    platinum_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("15.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="Скидка для Платины",
        help_text="Процент скидки для клиентов со статусом Платина",
    )

    class Meta:
        verbose_name = "Настройки программы лояльности"
        verbose_name_plural = "Настройки программы лояльности"

    def __str__(self):
        return "Настройки программы лояльности"

    @classmethod
    def get_settings(cls):
        """Получить настройки (создать если не существуют)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class CustomerStatus(models.TextChoices):
    """Статусы клиента в программе лояльности"""

    NONE = "NONE", "Без статуса"
    BRONZE = "BRONZE", "Бронза"
    SILVER = "SILVER", "Серебро"
    GOLD = "GOLD", "Золото"
    PLATINUM = "PLATINUM", "Платина"


class LoyaltyAccount(models.Model):
    """Аккаунт программы лояльности для пользователя"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="loyalty_account",
        verbose_name="Пользователь",
    )

    bonus_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Баланс бонусов",
        help_text="1 бонус = 1 рубль",
    )

    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Общая сумма покупок",
    )

    status = models.CharField(
        max_length=10,
        choices=CustomerStatus.choices,
        default=CustomerStatus.NONE,
        verbose_name="Статус",
    )

    personal_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="Персональная скидка",
        help_text="Дополнительная скидка для клиента (устанавливается вручную)",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        verbose_name = "Аккаунт лояльности"
        verbose_name_plural = "Аккаунты лояльности"
        ordering = ["-total_spent"]

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()} - {self.bonus_balance} бонусов"  # type: ignore

    def add_bonuses(self, amount: Decimal, description: str = "", save: bool = True):
        """Начислить бонусы"""
        if amount <= 0:
            return

        self.bonus_balance += amount
        if save:
            self.save()

        BonusTransaction.objects.create(
            loyalty_account=self,
            transaction_type=BonusTransaction.TransactionType.EARNED,
            amount=amount,
            description=description,
        )

    def spend_bonuses(self, amount: Decimal, description: str = ""):
        """Списать бонусы"""
        if amount <= 0 or amount > self.bonus_balance:
            return False

        self.bonus_balance -= amount
        self.save()

        BonusTransaction.objects.create(
            loyalty_account=self,
            transaction_type=BonusTransaction.TransactionType.SPENT,
            amount=amount,
            description=description,
        )
        return True

    def add_purchase(self, amount: Decimal):
        """Добавить сумму покупки и обновить статус"""
        if amount <= 0:
            return

        self.total_spent += amount
        self._update_status()
        self.save()

    def _update_status(self):
        """Обновить статус на основе общей суммы покупок"""
        settings = LoyaltySettings.get_settings()

        if self.total_spent >= settings.platinum_threshold:
            self.status = CustomerStatus.PLATINUM
        elif self.total_spent >= settings.gold_threshold:
            self.status = CustomerStatus.GOLD
        elif self.total_spent >= settings.silver_threshold:
            self.status = CustomerStatus.SILVER
        elif self.total_spent >= settings.bronze_threshold:
            self.status = CustomerStatus.BRONZE
        else:
            self.status = CustomerStatus.NONE

    def calculate_max_bonus_usage(self, service_price: Decimal) -> Decimal:
        """Рассчитать максимальную сумму бонусов для использования"""
        settings = LoyaltySettings.get_settings()
        max_amount = service_price * (settings.max_bonus_usage_percent / Decimal("100"))
        return min(max_amount, self.bonus_balance)

    def calculate_discount(self, base_price: Decimal) -> Decimal:
        """Рассчитать сумму скидки на основе статуса"""
        settings = LoyaltySettings.get_settings()

        discount_percent = Decimal("0.00")
        if self.status == CustomerStatus.BRONZE:
            discount_percent = settings.bronze_discount_percent
        elif self.status == CustomerStatus.SILVER:
            discount_percent = settings.silver_discount_percent
        elif self.status == CustomerStatus.GOLD:
            discount_percent = settings.gold_discount_percent
        elif self.status == CustomerStatus.PLATINUM:
            discount_percent = settings.platinum_discount_percent

        if self.personal_discount_percent > 0:
            discount_percent += self.personal_discount_percent

        if discount_percent <= 0:
            return Decimal("0.00")

        return base_price * (discount_percent / Decimal("100"))

    def calculate_final_price(
        self, base_price: Decimal, bonus_to_use: Decimal = Decimal("0.00")
    ) -> Decimal:
        """Рассчитать финальную цену с учетом скидки и бонусов"""
        discount_amount = self.calculate_discount(base_price)
        price_after_discount = base_price - discount_amount

        max_bonus = self.calculate_max_bonus_usage(price_after_discount)
        actual_bonus = min(bonus_to_use, max_bonus)
        final_price = price_after_discount - actual_bonus

        return max(final_price, Decimal("0.00"))


class BonusTransaction(models.Model):
    """История операций с бонусами"""

    class TransactionType(models.TextChoices):
        EARNED = "EARNED", "Начислено"
        SPENT = "SPENT", "Списано"
        EXPIRED = "EXPIRED", "Сгорело"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loyalty_account = models.ForeignKey(
        LoyaltyAccount,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Аккаунт лояльности",
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        verbose_name="Тип операции",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Сумма",
    )

    description = models.CharField(max_length=255, blank=True, verbose_name="Описание")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")

    class Meta:
        verbose_name = "Транзакция бонусов"
        verbose_name_plural = "Транзакции бонусов"
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.transaction_type == self.TransactionType.EARNED else "-"
        return f"{sign}{self.amount} - {self.get_transaction_type_display()}"  # type: ignore
