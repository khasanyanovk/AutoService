from django.urls import path
from . import api_views

urlpatterns = [
    path(
        "service-centers/",
        api_views.api_service_centers,
        name="api_service_centers",
    ),
    path(
        "service-centers/<uuid:service_center_id>/",
        api_views.api_service_center_detail,
        name="api_service_center_detail",
    ),
    path(
        "service-centers/<uuid:service_center_id>/services/",
        api_views.api_service_center_services,
        name="api_service_center_services",
    ),
]
