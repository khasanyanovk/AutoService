from django.db.models.signals import post_save, pre_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile, Appointment, Review
from .email_service import (
    send_appointment_status_changed_email,
    send_appointment_created_email,
    send_account_created_email,
    send_review_reply_email,
)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        try:
            if instance.email:
                send_account_created_email(instance)
        except Exception:
            pass


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "userprofile"):
        instance.userprofile.save()
    else:
        UserProfile.objects.create(user=instance)


@receiver(pre_save, sender=Appointment)
def capture_old_status(sender, instance: Appointment, **kwargs):
    """Store previous status on the instance for comparison in post_save."""
    if instance.pk:
        try:
            old = Appointment.objects.get(pk=instance.pk)
            instance._old_status = old.status  # type: ignore[attr-defined]
        except Appointment.DoesNotExist:
            instance._old_status = None  # type: ignore[attr-defined]
    else:
        instance._old_status = None  # type: ignore[attr-defined]


@receiver(post_save, sender=Appointment)
def notify_on_changes(sender, instance: Appointment, created: bool, **kwargs):
    try:
        if created:
            send_appointment_created_email(instance)
            return
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != instance.status:
            send_appointment_status_changed_email(instance)
    except Exception:
        pass


@receiver(pre_save, sender=Review)
def capture_old_admin_reply(sender, instance: Review, **kwargs):
    if instance.pk:
        try:
            old = Review.objects.get(pk=instance.pk)
            instance._old_admin_reply = old.admin_reply  # type: ignore[attr-defined]
        except Review.DoesNotExist:
            instance._old_admin_reply = None  # type: ignore[attr-defined]
    else:
        instance._old_admin_reply = None  # type: ignore[attr-defined]


@receiver(post_save, sender=Review)
def notify_on_admin_reply(sender, instance: Review, created: bool, **kwargs):
    try:
        prev = getattr(instance, "_old_admin_reply", None)
        if instance.admin_reply and (prev != instance.admin_reply):
            send_review_reply_email(instance)
    except Exception:
        pass
