import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from core.models import Appointment
from .models import Payment
from .services import create_payment as create_yookassa_payment, check_payment_status


@login_required
def create_payment(request, appointment_id):
    """Создание платежа для записи"""
    from decimal import Decimal
    from loyalty_program.models import LoyaltyAccount

    appointment = get_object_or_404(
        Appointment, id=appointment_id, car__owner=request.user
    )

    if appointment.status == "CANCELLED":
        messages.error(request, "Невозможно оплатить отмененную запись")
        return redirect("appointment_detail", appointment_id=appointment_id)

    existing_payment = Payment.objects.filter(
        appointment=appointment, status="succeeded"
    ).first()

    if existing_payment:
        messages.info(request, "Эта запись уже оплачена")
        return redirect("appointment_detail", appointment_id=appointment_id)

    try:
        loyalty_account, _ = LoyaltyAccount.objects.get_or_create(user=request.user)

        bonus_to_use = Decimal(request.GET.get("bonus_amount", "0") or "0")

        base_price = appointment.get_base_price()
        discount_amount = loyalty_account.calculate_discount(base_price)
        final_price = loyalty_account.calculate_final_price(base_price, bonus_to_use)

        max_bonus = loyalty_account.calculate_max_bonus_usage(
            base_price - discount_amount
        )
        actual_bonus_used = min(bonus_to_use, max_bonus, loyalty_account.bonus_balance)

        return_url = request.build_absolute_uri(f"/appointments/{appointment_id}/")

        payment = create_yookassa_payment(
            appointment=appointment,
            return_url=return_url,
            original_amount=base_price,
            discount_applied=discount_amount,
            bonus_used=actual_bonus_used,
            final_amount=final_price,
        )

        if payment.confirmation_url:
            return redirect(payment.confirmation_url)
        else:
            messages.error(request, "Ошибка создания платежа")
            return redirect("appointment_detail", appointment_id=appointment_id)

    except Exception as e:
        messages.error(request, f"Ошибка при создании платежа: {str(e)}")
        return redirect("appointment_detail", appointment_id=appointment_id)


@login_required
def check_payment(request, appointment_id):
    """Проверка статуса платежа"""
    appointment = get_object_or_404(
        Appointment, id=appointment_id, car__owner=request.user
    )

    latest_payment = (
        Payment.objects.filter(appointment=appointment).order_by("-created_at").first()
    )

    if latest_payment:
        check_payment_status(latest_payment)

        if latest_payment.status == "succeeded":
            messages.success(request, "Платеж успешно выполнен!")
        elif latest_payment.status == "canceled":
            messages.error(request, "Платеж отменен")
        else:
            messages.info(
                request, f"Статус платежа: {latest_payment.get_status_display()}"  # type: ignore
            )

    return redirect("appointment_detail", appointment_id=appointment_id)


@csrf_exempt
def yookassa_webhook(request):
    """Webhook для получения уведомлений от ЮKassa"""
    if request.method == "POST":
        try:
            event = json.loads(request.body)

            if event.get("event") == "payment.succeeded":
                payment_id = event["object"]["id"]

                try:
                    payment = Payment.objects.get(payment_id=payment_id)
                    check_payment_status(payment)
                except Payment.DoesNotExist:
                    pass

            return HttpResponse(status=200)
        except Exception as e:
            print(f"Webhook error: {e}")
            return HttpResponse(status=400)

    return HttpResponse(status=405)
