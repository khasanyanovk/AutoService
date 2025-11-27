"""
Сервис для работы с платежами через ЮKassa
"""

from django.conf import settings
from django.utils import timezone
from yookassa import Configuration, Payment as YooPayment  # type: ignore
from .models import Payment
from core.models import Appointment

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def create_payment(
    appointment: Appointment,
    return_url: str,
    original_amount=None,
    discount_applied=None,
    bonus_used=None,
    final_amount=None,
) -> Payment:
    """
    Создает платеж для записи

    Args:
        appointment: Объект записи
        return_url: URL для возврата после оплаты
        original_amount: Исходная цена услуги
        discount_applied: Применённая скидка
        bonus_used: Использованные бонусы
        final_amount: Финальная сумма к оплате

    Returns:
        Payment: Созданный объект платежа
    """
    from decimal import Decimal

    existing_payment = Payment.objects.filter(
        appointment=appointment, status="pending"
    ).first()

    if existing_payment:
        return existing_payment

    if final_amount is None:
        final_amount = appointment.get_base_price()
    if original_amount is None:
        original_amount = appointment.get_base_price()
    if discount_applied is None:
        discount_applied = Decimal("0")
    if bonus_used is None:
        bonus_used = Decimal("0")

    description = f"Оплата услуги '{appointment.service_type.name}' по адресу: {appointment.service_center.address}"  # type: ignore

    payment_data = {
        "amount": {"value": str(final_amount), "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": description,
        "metadata": {"appointment_id": str(appointment.id)},
    }

    yoo_payment = YooPayment.create(payment_data)

    payment = Payment.objects.create(
        appointment=appointment,
        payment_id=yoo_payment.id,
        original_amount=original_amount,
        discount_applied=discount_applied,
        bonus_used=bonus_used,
        amount=final_amount,
        status=yoo_payment.status,
        description=description,
        confirmation_url=yoo_payment.confirmation.confirmation_url,  # type: ignore
    )

    return payment


def check_payment_status(payment: Payment) -> Payment:
    """
    Проверяет статус платежа в ЮKassa и обновляет его

    Args:
        payment: Объект платежа

    Returns:
        Payment: Обновленный объект платежа
    """
    yoo_payment = YooPayment.find_one(payment.payment_id)

    old_status = payment.status
    payment.status = yoo_payment.status  # type: ignore

    if yoo_payment.status == "succeeded" and old_status != "succeeded":
        payment.paid_at = timezone.now()

    payment.save()
    return payment


def get_payment_info(payment_id: str) -> dict:
    """
    Получает информацию о платеже из ЮKassa

    Args:
        payment_id: ID платежа в ЮKassa

    Returns:
        dict: Информация о платеже
    """
    try:
        yoo_payment = YooPayment.find_one(payment_id)
        return {
            "id": yoo_payment.id,
            "status": yoo_payment.status,
            "amount": yoo_payment.amount.value,  # type: ignore
            "currency": yoo_payment.amount.currency,  # type: ignore
            "created_at": yoo_payment.created_at,
            "paid": yoo_payment.paid,
        }
    except Exception as e:
        return {"error": str(e)}


def cancel_payment(payment: Payment) -> bool:
    """
    Отменяет платеж

    Args:
        payment: Объект платежа

    Returns:
        bool: True если отменен успешно
    """
    try:
        yoo_payment = YooPayment.find_one(payment.payment_id)

        if yoo_payment.status == "pending":
            payment.status = "canceled"
            payment.save()
            return True
        return False
    except Exception as e:
        print(f"Error canceling payment: {e}")
        return False
