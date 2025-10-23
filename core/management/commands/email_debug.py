from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Send a test email and print effective email settings. Usage: manage.py email_debug recipient@example.com [--subject S] [--body B]"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("recipient", type=str, help="Recipient email address")
        parser.add_argument(
            "--subject",
            type=str,
            default="AutoService test email",
            help="Email subject",
        )
        parser.add_argument(
            "--body",
            type=str,
            default="This is a test email from AutoService.",
            help="Plain text body",
        )

    def handle(self, *args, **options):
        recipient = options["recipient"]
        subject = options["subject"]
        body = options["body"]

        self.stdout.write("Effective email settings:")
        self.stdout.write(f"  BACKEND: {getattr(settings, 'EMAIL_BACKEND', None)}")
        self.stdout.write(f"  HOST: {getattr(settings, 'EMAIL_HOST', None)}")
        self.stdout.write(f"  PORT: {getattr(settings, 'EMAIL_PORT', None)}")
        self.stdout.write(f"  USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', None)}")
        self.stdout.write(f"  USE_SSL: {getattr(settings, 'EMAIL_USE_SSL', None)}")
        self.stdout.write(f"  TIMEOUT: {getattr(settings, 'EMAIL_TIMEOUT', None)}")
        self.stdout.write(f"  FROM: {getattr(settings, 'DEFAULT_FROM_EMAIL', None)}")
        self.stdout.write("")

        try:
            sent = send_mail(
                subject,
                body,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"send_mail returned: {sent}"))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"send_mail failed: {exc}"))
            raise
