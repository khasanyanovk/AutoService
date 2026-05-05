from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import ServiceCenter, ServiceType, WorkingHours


@require_GET
def api_service_centers(request):
    """List all service centers as JSON."""
    centers = (
        ServiceCenter.objects.all()
        .prefetch_related("working_hours")
        .order_by("address")
    )

    data = []
    for center in centers:
        working_hours = []
        for wh in center.working_hours.all().order_by("day_of_week"):
            working_hours.append(
                {
                    "day_of_week": wh.day_of_week,
                    "day_name": wh.get_day_of_week_display(),
                    "start_time": wh.start_time.strftime("%H:%M") if wh.start_time else None,
                    "end_time": wh.end_time.strftime("%H:%M") if wh.end_time else None,
                    "lunch_start": wh.lunch_start.strftime("%H:%M") if wh.lunch_start else None,
                    "lunch_end": wh.lunch_end.strftime("%H:%M") if wh.lunch_end else None,
                    "is_working": wh.is_working,
                }
            )

        data.append(
            {
                "id": str(center.id),
                "address": center.address,
                "phone": center.phone,
                "opening_hours": center.opening_hours,
                "photo_url": request.build_absolute_uri(center.get_photo_url()),
                "working_hours": working_hours,
            }
        )

    return JsonResponse({"service_centers": data})


@require_GET
def api_service_center_detail(request, service_center_id):
    """Detail of a single service center including its active services."""
    try:
        center = (
            ServiceCenter.objects.prefetch_related("working_hours")
            .get(id=service_center_id)
        )
    except ServiceCenter.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    working_hours = []
    for wh in center.working_hours.all().order_by("day_of_week"):
        working_hours.append(
            {
                "day_of_week": wh.day_of_week,
                "day_name": wh.get_day_of_week_display(),
                "start_time": wh.start_time.strftime("%H:%M") if wh.start_time else None,
                "end_time": wh.end_time.strftime("%H:%M") if wh.end_time else None,
                "lunch_start": wh.lunch_start.strftime("%H:%M") if wh.lunch_start else None,
                "lunch_end": wh.lunch_end.strftime("%H:%M") if wh.lunch_end else None,
                "is_working": wh.is_working,
            }
        )

    services = []
    for s in ServiceType.objects.filter(service_center=center, is_active=True).order_by("name"):
        services.append(
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "duration": s.duration,
                "price": str(s.price),
            }
        )

    data = {
        "id": str(center.id),
        "address": center.address,
        "phone": center.phone,
        "opening_hours": center.opening_hours,
        "photo_url": request.build_absolute_uri(center.get_photo_url()),
        "working_hours": working_hours,
        "services": services,
    }

    return JsonResponse(data)


@require_GET
def api_service_center_services(request, service_center_id):
    """List active services for a given service center."""
    try:
        center = ServiceCenter.objects.get(id=service_center_id)
    except ServiceCenter.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    services = []
    for s in ServiceType.objects.filter(service_center=center, is_active=True).order_by("name"):
        services.append(
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "duration": s.duration,
                "price": str(s.price),
            }
        )

    return JsonResponse({"services": services})
