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
    ProfileViewSet,
    AdminAppointmentViewSet,
    AdminStatsViewSet,
    AdminReviewViewSet,
    AdminSlotViewSet,
    AdminClientViewSet,
    AdminServiceTypeViewSet,      
    AdminServiceCenterViewSet,    
    AdminEmployeeViewSet,         
    AdminDashboardViewSet,
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
router.register(r'admin-panel/appointments', AdminAppointmentViewSet, basename='admin-appointments')
router.register(r'admin-panel/stats', AdminStatsViewSet, basename='admin-stats')
router.register(r'admin-panel/reviews', AdminReviewViewSet, basename='admin-reviews')
router.register(r'admin-panel/slots', AdminSlotViewSet, basename='admin-slots')
router.register(r'admin-panel/clients', AdminClientViewSet, basename='admin-clients')
router.register(r'admin-panel/services', AdminServiceTypeViewSet, basename='admin-services')
router.register(r'admin-panel/centers', AdminServiceCenterViewSet, basename='admin-centers')
router.register(r'admin-panel/employees', AdminEmployeeViewSet, basename='admin-employees')
router.register(r'admin-panel/dashboard', AdminDashboardViewSet, basename='admin-dashboard')

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='api_register'),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]