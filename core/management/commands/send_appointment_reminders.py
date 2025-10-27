from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from core.models import Appointment
from core.email_service import send_appointment_reminder_email


class Command(BaseCommand):
    help = (
        "Send reminder emails. Default: all appointments scheduled for tomorrow (status=SCHEDULED). "
        "Use --exact-24h to send only for appointments ~24h from now (within window)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--exact-24h",
            action="store_true",
            help="Send reminders for appointments ~24 hours from now (time window).",
        )
        parser.add_argument(
            "--window-minutes",
            type=int,
            default=60,
            help="Time window in minutes around 24h-from-now when using --exact-24h (default 60).",
        )

    def handle(self, *args, **options):
        now = timezone.localtime(timezone.now())
        sent = 0

        if options.get("exact_24h"):
            target_dt = now + timedelta(hours=24)
            lower = target_dt - timedelta(minutes=options.get("window_minutes", 60))
            upper = target_dt + timedelta(minutes=options.get("window_minutes", 60))

            qs = Appointment.objects.filter(
                status="SCHEDULED", scheduled_date=target_dt.date()
            ).select_related("car", "car__owner", "service_type", "service_center")

            def in_window(appt):
                try:
                    appt_dt = datetime.combine(appt.scheduled_date, appt.scheduled_time)
                    appt_dt = timezone.make_aware(appt_dt, now.tzinfo)
                    return lower <= appt_dt <= upper
                except Exception:
                    return False

            for appt in qs:
                if in_window(appt):
                    try:
                        send_appointment_reminder_email(appt)
                        sent += 1
                    except Exception:
                        pass

            self.stdout.write(
                self.style.SUCCESS(
                    f"Reminders sent (exact-24h, window {options.get('window_minutes',60)}m): {sent}"
                )
            )
            return

        tomorrow = now.date() + timedelta(days=1)
        qs = (
            Appointment.objects.filter(status="SCHEDULED", scheduled_date=tomorrow)
            .select_related("car", "car__owner", "service_type", "service_center")
            .order_by("scheduled_time")
        )
        for appt in qs:
            try:
                send_appointment_reminder_email(appt)
                sent += 1
            except Exception:
                pass

        self.stdout.write(
            self.style.SUCCESS(f"Reminders sent (tomorrow): {sent} for {tomorrow}")
        )
