from django.apps import AppConfig


class LoyaltyProgramConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "loyalty_program"
    verbose_name = "Программа лояльности"

    def ready(self):
        import loyalty_program.signals  # noqa
