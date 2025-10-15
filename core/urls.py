from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("car/add/", views.add_car, name="add_car"),
    path("car/<uuid:car_id>/edit/", views.edit_car, name="edit_car"),
    path("car/<uuid:car_id>/delete/", views.delete_car, name="delete_car"),
    path("ajax/load-models/", views.load_models, name="load_models"),
    path("booking/", views.service_booking, name="service_booking"),
    path("appointments/", views.appointment_list, name="appointment_list"),
    path(
        "appointments/<uuid:appointment_id>/cancel/",
        views.cancel_appointment,
        name="cancel_appointment",
    ),
    path("ajax/get-time-slots/", views.get_available_time_slots, name="get_time_slots"),
    path("about/", views.about, name="about"),
    path("admin-branches/", views.admin_branches, name="admin_branches"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
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
        "admin-api/service-center/<uuid:service_center_id>/day-schedule/",
        views.admin_api_day_schedule,
        name="admin_api_day_schedule",
    ),
    path(
        "admin-dashboard/appointment/<uuid:appointment_id>/",
        views.admin_appointment_detail,
        name="admin_appointment_detail",
    ),
    path(
        "admin-api/appointments/",
        views.admin_api_appointments,
        name="admin_api_appointments",
    ),
    path(
        "get-available-services/",
        views.get_available_services,
        name="get_available_services",
    ),
    path("get-service-details/", views.get_service_details, name="get_service_details"),
]
