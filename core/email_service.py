import threading
import logging
from typing import Iterable, List
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.models import User


def admin_recipients() -> List[str]:
    if getattr(settings, "NOTIFY_ADMINS_EMAILS", None):
        return [e for e in settings.NOTIFY_ADMINS_EMAILS if e]
    return [u.email for u in User.objects.filter(is_staff=True).exclude(email="")]


def _render_template(template_base: str, context: dict) -> tuple[str, str | None]:
    """Render text and html bodies for given template base name.
    Expects files: emails/{template_base}.txt and optional emails/{template_base}.html
    """
    text_body = render_to_string(f"emails/{template_base}.txt", context)
    ctx = dict(context)
    try:
        static_url = getattr(settings, "STATIC_URL", "/static/")
        logo_url = f"{static_url}core/img/logo.png"
        if "logo_url" not in ctx:
            ctx["logo_url"] = logo_url
        html_body = render_to_string(f"emails/{template_base}.html", ctx)
    except Exception:
        html_body = None
    return text_body, html_body


logger = logging.getLogger(__name__)


def _send_async(subject: str, recipients: Iterable[str], text: str, html: str | None):
    recipients = [e for e in recipients if e]
    if not recipients:
        return

    def _runner():
        try:
            send_mail(
                subject,
                text,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                list(recipients),
                fail_silently=not getattr(settings, "DEBUG", False),
                html_message=html,
            )
            logger.info(
                "Email queued/sent: subject='%s', to=%s, from=%s",
                subject,
                recipients,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
            )
        except Exception as exc:
            # Ensure visibility even in threads
            logger.error("Email send failed: %s", exc, exc_info=True)
            if getattr(settings, "DEBUG", False):
                # Best-effort console output during development
                print(f"[email_service] send failed: {exc}")

    threading.Thread(target=_runner, daemon=True).start()


def _appointment_context(appt) -> dict:
    return {
        "user": appt.car.owner,
        "appointment": appt,
        "car": appt.car,
        "service": appt.service_type,
        "service_center": appt.service_center,
        "scheduled_date": appt.scheduled_date,
        "scheduled_time": appt.scheduled_time,
        "status": appt.status,
    }


def send_appointment_created_email(appt) -> None:
    ctx = _appointment_context(appt)
    text, html = _render_template("appointment_created", ctx)
    subject_user = "Подтверждение записи"
    _send_async(subject_user, [appt.car.owner.email], text, html)

    admins = admin_recipients()
    if admins:
        subject_admin = f"Новая запись — {appt.service_center}"
        _send_async(subject_admin, admins, text, html)


def send_appointment_status_changed_email(appt) -> None:
    ctx = _appointment_context(appt)
    text, html = _render_template("appointment_status_changed", ctx)
    subject = f"Статус вашей записи: {dict(getattr(appt, 'STATUS_CHOICES', [] )).get(appt.status, appt.status)}"
    _send_async(subject, [appt.car.owner.email], text, html)

    admins = admin_recipients()
    if admins:
        subject_admin = f"Статус изменён — {appt.service_center}"
        _send_async(subject_admin, admins, text, html)


def send_appointment_cancelled_email(appt) -> None:
    ctx = _appointment_context(appt)
    text, html = _render_template("appointment_cancelled", ctx)
    subject = "Ваша запись отменена"
    _send_async(subject, [ctx["user"].email], text, html)
    print(ctx["user"].email)

    admins = admin_recipients()
    if admins:
        subject_admin = f"Запись отменена — {appt.service_center}"
        _send_async(subject_admin, admins, text, html)


def send_review_reply_email(review) -> None:
    if not review.admin_reply:
        return
    ctx = {
        "user": review.user,
        "service_center": review.service_center,
        "rating": review.rating,
        "comment": review.comment,
        "admin_reply": review.admin_reply,
        "admin_reply_at": review.admin_reply_at,
    }
    text, html = _render_template("review_admin_reply", ctx)
    subject = "Ответ на ваш отзыв"
    _send_async(subject, [review.user.email], text, html)


def send_account_created_email(user: User) -> None:
    ctx = {"user": user}
    text, html = _render_template("account_created", ctx)
    subject = "Добро пожаловать в AutoService"
    _send_async(subject, [user.email], text, html)


def send_appointment_reminder_email(appt) -> None:
    """Notify the user about an upcoming appointment (typically ~24h before)."""
    ctx = _appointment_context(appt)
    text, html = _render_template("appointment_reminder", ctx)
    subject = "Напоминание о вашей записи"
    _send_async(subject, [appt.car.owner.email], text, html)
