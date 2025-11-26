"""
Сигналы для программы лояльности
"""

from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from core.models import Appointment
from payments.models import Payment
from .models import LoyaltyAccount, LoyaltySettings


@receiver(post_save, sender=User)
def create_loyalty_account(sender, instance, created, **kwargs):
    """Создать аккаунт лояльности при регистрации пользователя"""
    if created:
        LoyaltyAccount.objects.get_or_create(user=instance)


@receiver(post_save, sender=Payment)
def process_online_payment_bonus(sender, instance, created, **kwargs):
    """Начислить бонусы за онлайн оплату и списать использованные бонусы"""
    if instance.status == "succeeded":
        try:
            appointment = instance.appointment
            user = appointment.car.owner

            loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=user)

            bonus_description = f"Онлайн оплата услуги #{appointment.id}"
            if loyalty_account.transactions.filter(
                description=bonus_description
            ).exists():
                return

            if instance.bonus_used > 0:
                loyalty_account.spend_bonuses(
                    amount=instance.bonus_used,
                    description=f"Оплата услуги #{appointment.id}",
                )

            appointment.paid_amount = instance.amount
            appointment.save(update_fields=["paid_amount"])

            settings = LoyaltySettings.get_settings()
            bonus_amount = instance.amount * (
                settings.online_payment_bonus_percent / Decimal("100")
            )

            loyalty_account.add_bonuses(
                amount=bonus_amount, description=bonus_description, save=False
            )

            loyalty_account.add_purchase(instance.amount)

        except Exception as e:
            print(f"[loyalty_program] Error processing online payment bonus: {e}")


@receiver(post_save, sender=Appointment)
def process_offline_payment_bonus(sender, instance, created, **kwargs):
    """Начислить бонусы когда услуга выполнена (оплата в центре)"""
    if instance.status == "COMPLETED":
        try:
            user = instance.car.owner

            loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=user)

            if instance.payments.filter(status="succeeded").exists():
                return

            bonus_description = f"Оплата в центре за услугу #{instance.id}"
            if loyalty_account.transactions.filter(
                description=bonus_description
            ).exists():
                return

            settings = LoyaltySettings.get_settings()
            service_price = instance.get_final_price()
            bonus_amount = service_price * (
                settings.offline_payment_bonus_percent / Decimal("100")
            )

            loyalty_account.add_bonuses(
                amount=bonus_amount, description=bonus_description, save=False
            )

            loyalty_account.add_purchase(service_price)

        except Exception as e:
            print(f"[loyalty_program] Error processing offline payment bonus: {e}")
