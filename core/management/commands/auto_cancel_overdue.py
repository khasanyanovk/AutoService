from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from core.models import Appointment


class Command(BaseCommand):
    help = "Auto-cancel overdue appointments that are still SCHEDULED."

    def handle(self, *args, **options):
        now = timezone.localtime(timezone.now())
        today = now.date()
        now_time = now.time()

        qs = Appointment.objects.filter(status="SCHEDULED").filter(
            Q(scheduled_date__lt=today)
            | Q(scheduled_date=today, end_time__lte=now_time)
        )
        count = qs.count()
        if count:
            qs.update(status="CANCELLED", updated_at=now)
        self.stdout.write(self.style.SUCCESS(f"Auto-cancelled: {count}"))
