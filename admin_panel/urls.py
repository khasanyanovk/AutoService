from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-branches/", views.admin_branches, name="admin_branches"),
    path(
        "admin-branches/create/",
        views.admin_service_center_create,
        name="admin_service_center_create",
    ),
    path("admin-users/", views.admin_users, name="admin_users"),
    path("admin-services/", views.admin_services, name="admin_services"),
    path(
        "admin-services/create/",
        views.admin_service_create,
        name="admin_service_create",
    ),
    path(
        "admin-services/<uuid:service_id>/edit/",
        views.admin_service_edit,
        name="admin_service_edit",
    ),
    path(
        "admin-user/<int:user_id>/",
        views.admin_user_detail,
        name="admin_user_detail",
    ),
    path(
        "admin-user/<int:user_id>/edit/",
        views.admin_user_edit,
        name="admin_user_edit",
    ),
    path(
        "admin-user/<int:user_id>/stats/",
        views.admin_user_stats,
        name="admin_user_stats",
    ),
    path(
        "admin-user/<int:user_id>/delete/",
        views.admin_user_delete,
        name="admin_user_delete",
    ),
    path(
        "admin-dashboard/service-center/<uuid:service_center_id>/",
        views.admin_service_center_detail,
        name="admin_service_center_detail",
    ),
    path(
        "admin-dashboard/service-center/<uuid:service_center_id>/edit/",
        views.admin_service_center_edit,
        name="admin_service_center_edit",
    ),
    path(
        "admin-dashboard/service-center/<uuid:service_center_id>/delete/",
        views.admin_service_center_delete,
        name="admin_service_center_delete",
    ),
    path(
        "admin-dashboard/appointment/<uuid:appointment_id>/",
        views.admin_appointment_detail,
        name="admin_appointment_detail",
    ),
    path(
        "admin-dashboard/appointments/",
        views.admin_appointments,
        name="admin_appointments",
    ),
    path(
        "admin-api/service-center/<uuid:service_center_id>/day-schedule/",
        views.admin_api_day_schedule,
        name="admin_api_day_schedule",
    ),
    path(
        "admin-api/appointments/",
        views.admin_api_appointments,
        name="admin_api_appointments",
    ),
    path(
        "admin-api/appointment/<uuid:appointment_id>/update/",
        views.admin_api_update_appointment,
        name="admin_api_update_appointment",
    ),
    path(
        "admin-api/overall-visits/",
        views.admin_api_overall_visits,
        name="admin_api_overall_visits",
    ),
    path(
        "admin-api/overall-statuses/",
        views.admin_api_overall_statuses,
        name="admin_api_overall_statuses",
    ),
]
