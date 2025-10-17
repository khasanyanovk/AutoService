from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-branches/", views.admin_branches, name="admin_branches"),
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
