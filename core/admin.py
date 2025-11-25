from django.contrib import admin
from .models import (
    CarBrand,
    CarModel,
    Car,
    ServiceCenter,
    ServiceType,
    Appointment,
    WorkingHours,
    UserProfile,
    Review,
    BlockedTimeSlot,
    Payment,
)

admin.site.register(CarBrand)
admin.site.register(CarModel)
admin.site.register(Car)
admin.site.register(ServiceCenter)
admin.site.register(ServiceType)
admin.site.register(Appointment)
admin.site.register(WorkingHours)
admin.site.register(UserProfile)
admin.site.register(Review)
admin.site.register(BlockedTimeSlot)
admin.site.register(Payment)
