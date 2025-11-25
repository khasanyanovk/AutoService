from django.urls import path
from . import views

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
    path(
        "appointments/<uuid:appointment_id>/",
        views.appointment_detail,
        name="appointment_detail",
    ),
    path(
        "appointments/<uuid:appointment_id>/cancel/",
        views.cancel_appointment,
        name="cancel_appointment",
    ),
    path(
        "ajax/get-time-slots/",
        views.get_available_time_slots,
        name="get_time_slots",
    ),
    path("about/", views.about, name="about"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("terms-of-service/", views.terms_of_service, name="terms_of_service"),
    path("branches/", views.branches, name="branches"),
    path(
        "branches/<uuid:service_center_id>/", views.branch_detail, name="branch_detail"
    ),
    path(
        "get-available-services/",
        views.get_available_services,
        name="get_available_services",
    ),
    path("get-service-details/", views.get_service_details, name="get_service_details"),
]
