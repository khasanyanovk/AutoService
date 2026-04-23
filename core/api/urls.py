from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CarViewSet,
    AppointmentViewSet,
    ServiceTypeViewSet,
    ServiceCenterViewSet,
    CarBrandViewSet,
    CarModelViewSet,
    MyTokenObtainPairView,
    ProfileViewSet
)
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterAPIView


router = DefaultRouter()
router.register(r'cars', CarViewSet, basename='cars')
router.register(r'appointments', AppointmentViewSet, basename='appointments')
router.register(r'service-types', ServiceTypeViewSet, basename='service-types')
router.register(r'service-centers', ServiceCenterViewSet, basename='service-centers')
router.register(r'car-brands', CarBrandViewSet, basename='car-brands')
router.register(r'car-models', CarModelViewSet, basename='car-models')
router.register(r'profile', ProfileViewSet, basename='profile')

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='api_register'),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]