from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path(
        "appointments/<uuid:appointment_id>/pay/",
        views.create_payment,
        name="create_payment",
    ),
    path(
        "appointments/<uuid:appointment_id>/check-payment/",
        views.check_payment,
        name="check_payment",
    ),
    path("webhook/", views.yookassa_webhook, name="yookassa_webhook"),
]
