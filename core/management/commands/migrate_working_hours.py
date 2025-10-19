from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import ServiceCenter, WorkingHours


class Command(BaseCommand):
    help = "Миграция рабочих часов: копирует старые записи (без филиала) для каждого филиала"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-old",
            action="store_true",
            help="Удалить старые записи WorkingHours без привязки к филиалу после копирования",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        old_rows = list(WorkingHours.objects.filter(service_center__isnull=True))
        centers = list(ServiceCenter.objects.all())
        created_count = 0
        skipped = 0

        if not old_rows:
            self.stdout.write(
                self.style.WARNING("Нет старых записей рабочих часов для копирования")
            )
            return

        for sc in centers:
            for wh in old_rows:
                obj, created = WorkingHours.objects.get_or_create(
                    service_center=sc,
                    day_of_week=wh.day_of_week,
                    defaults={
                        "start_time": wh.start_time,
                        "end_time": wh.end_time,
                        "lunch_start": getattr(wh, "lunch_start", None),
                        "lunch_end": getattr(wh, "lunch_end", None),
                        "is_working": wh.is_working,
                    },
                )
                if created:
                    created_count += 1
                else:
                    skipped += 1

        if options.get("delete_old"):
            WorkingHours.objects.filter(service_center__isnull=True).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Создано {created_count} записей рабочих часов, пропущено {skipped}"
            )
        )
