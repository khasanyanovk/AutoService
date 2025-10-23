from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Appointment
from core.email_service import send_appointment_reminder_email


class Command(BaseCommand):
    help = "Send reminder emails for appointments scheduled for tomorrow (status=SCHEDULED)."

    def handle(self, *args, **options):
        now = timezone.localtime(timezone.now())
        tomorrow = now.date() + timedelta(days=1)

        qs = (
            Appointment.objects.filter(status="SCHEDULED", scheduled_date=tomorrow)
            .select_related("car", "car__owner", "service_type", "service_center")
            .order_by("scheduled_time")
        )

        sent = 0
        for appt in qs:
            try:
                send_appointment_reminder_email(appt)
                sent += 1
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(f"Reminders sent: {sent} for {tomorrow}"))
