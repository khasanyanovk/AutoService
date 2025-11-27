from django.contrib import admin
from .models import LoyaltySettings, LoyaltyAccount, BonusTransaction


@admin.register(LoyaltySettings)
class LoyaltySettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Настройки начисления бонусов",
            {
                "fields": (
                    "online_payment_bonus_percent",
                    "offline_payment_bonus_percent",
                    "max_bonus_usage_percent",
                )
            },
        ),
        (
            "Пороги для статусов",
            {
                "fields": (
                    "bronze_threshold",
                    "silver_threshold",
                    "gold_threshold",
                    "platinum_threshold",
                )
            },
        ),
        (
            "Скидки по статусам",
            {
                "fields": (
                    "bronze_discount_percent",
                    "silver_discount_percent",
                    "gold_discount_percent",
                    "platinum_discount_percent",
                ),
                "description": "Процент скидки для каждого статуса клиента. Скидка по статусу суммируется с персональной скидкой.",
            },
        ),
    )

    def has_add_permission(self, request):
        return not LoyaltySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "bonus_balance",
        "total_spent",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (
            "Информация о пользователе",
            {"fields": ("user",)},
        ),
        (
            "Баланс и статус",
            {
                "fields": (
                    "bonus_balance",
                    "total_spent",
                    "status",
                    "personal_discount_percent",
                )
            },
        ),
        (
            "Даты",
            {"fields": ("created_at", "updated_at")},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(BonusTransaction)
class BonusTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "loyalty_account",
        "transaction_type",
        "amount",
        "description",
        "created_at",
    )
    list_filter = ("transaction_type", "created_at")
    search_fields = (
        "loyalty_account__user__username",
        "loyalty_account__user__email",
        "description",
    )
    readonly_fields = ("id", "created_at")
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("loyalty_account__user")
