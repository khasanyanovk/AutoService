from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.db.models.functions import ExtractWeekDay
from django.utils import timezone
import json

from core.views import generate_time_slots
from core.models import (
    ServiceType,
    Appointment,
    WorkingHours,
    ServiceCenter,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.forms import (
    ServiceCenterEditForm,
)
from django.http import JsonResponse
from datetime import datetime, timedelta
from .decorators import admin_required


@login_required
@admin_required
def admin_dashboard(request):
    """Главная страница администратора"""
    service_centers = ServiceCenter.objects.all()

    today = timezone.localtime(timezone.now()).date()

    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(scheduled_date=today).count()
    pending_appointments = Appointment.objects.filter(status="SCHEDULED").count()
    in_progress_appointments = Appointment.objects.filter(status="IN_PROGRESS").count()
    completed_30d = Appointment.objects.filter(
        status="COMPLETED", scheduled_date__gte=today - timedelta(days=30)
    ).count()
    cancelled_30d = Appointment.objects.filter(
        status="CANCELLED", scheduled_date__gte=today - timedelta(days=30)
    ).count()
    active_services = ServiceType.objects.filter(is_active=True).count()
    branches_count = ServiceCenter.objects.count()
    customers_count = Appointment.objects.values("car__owner").distinct().count()

    upcoming_appointments = (
        Appointment.objects.filter(
            scheduled_date__gte=timezone.localtime(timezone.now()).date()
        )
        .select_related("service_center", "car", "service_type", "car__owner")
        .order_by("scheduled_date", "scheduled_time")[:12]
    )

    chart_start = today - timedelta(days=6)
    visits_qs = (
        Appointment.objects.filter(
            scheduled_date__gte=chart_start, scheduled_date__lte=today
        )
        .values("scheduled_date")
        .annotate(count=Count("id"))
        .order_by("scheduled_date")
    )
    overall_visits_labels = []
    overall_visits_data = []
    current = chart_start
    while current <= today:
        overall_visits_labels.append(current.strftime("%d.%m"))
        found = next((v for v in visits_qs if v["scheduled_date"] == current), None)
        overall_visits_data.append(found["count"] if found else 0)
        current += timedelta(days=1)

    services_qs = (
        Appointment.objects.filter(status__in=["SCHEDULED", "IN_PROGRESS", "COMPLETED"])
        .values("service_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    overall_service_labels = [s["service_type__name"] for s in services_qs]
    overall_service_data = [s["count"] for s in services_qs]

    status_label_map = {k: v for k, v in Appointment.STATUS_CHOICES}
    statuses_qs = (
        Appointment.objects.filter(
            scheduled_date__gte=today - timedelta(days=6), scheduled_date__lte=today
        )
        .values("status")
        .annotate(count=Count("id"))
    )
    overall_statuses = [
        {
            "status": row["status"],
            "label": status_label_map.get(row["status"], row["status"]),
            "count": row["count"],
        }
        for row in statuses_qs
    ]

    context = {
        "service_centers": service_centers,
        "total_appointments": total_appointments,
        "today_appointments": today_appointments,
        "pending_appointments": pending_appointments,
        "in_progress_appointments": in_progress_appointments,
        "completed_30d": completed_30d,
        "cancelled_30d": cancelled_30d,
        "active_services": active_services,
        "branches_count": branches_count,
        "customers_count": customers_count,
        "upcoming_appointments": upcoming_appointments,
        "overall_visits_labels": overall_visits_labels,
        "overall_visits_data": overall_visits_data,
        "overall_service_labels": overall_service_labels,
        "overall_service_data": overall_service_data,
        "overall_statuses": overall_statuses,
    }
    return render(request, "admin_panel/admin_dashboard.html", context)


@login_required
@admin_required
def admin_appointments(request):
    """Заглушка для страницы управления всеми записями (будет реализована позже)."""
    return render(request, "admin_panel/admin_appointments.html")


@login_required
@admin_required
def admin_api_overall_statuses(request):
    """AJAX: Статистика по статусам записей за период (неделя/месяц) по всем филиалам"""
    today = timezone.localtime(timezone.now()).date()
    period = request.GET.get("period", "week")
    if period == "month":
        start = today - timedelta(days=29)
    else:
        start = today - timedelta(days=6)

    qs = (
        Appointment.objects.filter(scheduled_date__gte=start, scheduled_date__lte=today)
        .values("status")
        .annotate(count=Count("id"))
    )
    status_label_map = {k: v for k, v in Appointment.STATUS_CHOICES}
    data = [
        {
            "status": row["status"],
            "label": status_label_map.get(row["status"], row["status"]),
            "count": row["count"],
        }
        for row in qs
    ]
    return JsonResponse({"items": data})


@login_required
@admin_required
def admin_api_overall_visits(request):
    """AJAX: Общая посещаемость по всем филиалам для периода неделя/месяц"""
    today = timezone.localtime(timezone.now()).date()
    period = request.GET.get("period", "week")
    if period == "month":
        chart_start = today - timedelta(days=29)
    else:
        chart_start = today - timedelta(days=6)

    visits_qs = (
        Appointment.objects.filter(
            scheduled_date__gte=chart_start, scheduled_date__lte=today
        )
        .values("scheduled_date")
        .annotate(count=Count("id"))
        .order_by("scheduled_date")
    )

    by_date = {row["scheduled_date"]: row["count"] for row in visits_qs}
    labels = []
    data = []
    current = chart_start
    while current <= today:
        labels.append(current.strftime("%d.%m"))
        data.append(by_date.get(current, 0))
        current += timedelta(days=1)

    return JsonResponse({"labels": labels, "data": data})


@login_required
@admin_required
def admin_service_center_detail(request, service_center_id):
    """Детальная страница автосервиса с календарем, расписанием на сегодня и статистикой"""
    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    today = timezone.localtime(timezone.now()).date()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))
    selected_date_str = request.GET.get("date")
    selected_date = (
        datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        if selected_date_str
        else today
    )
    period = request.GET.get("period", "week")

    appointments = (
        Appointment.objects.filter(
            scheduled_date__year=year,
            scheduled_date__month=month,
            service_center=service_center,
        )
        .select_related("car", "service_type", "car__owner")
        .order_by("scheduled_date", "scheduled_time")
    )

    calendar_events = []
    for appointment in appointments:
        calendar_events.append(
            {
                "id": str(appointment.id),
                "title": f"{appointment.car} - {appointment.service_type.name}",
                "start": f"{appointment.scheduled_date}T{appointment.scheduled_time}",
                "end": (
                    f"{appointment.scheduled_date}T{appointment.end_time}"
                    if appointment.end_time
                    else f"{appointment.scheduled_date}T{appointment.scheduled_time}"
                ),
                "status": appointment.status,
                "user": appointment.car.owner.get_full_name()
                or appointment.car.owner.username,
                "car": str(appointment.car),
                "service": appointment.service_type.name,
            }
        )

    start_date = today - timedelta(days=30)
    service_stats = (
        Appointment.objects.filter(
            scheduled_date__gte=start_date,
            scheduled_date__lte=today,
            service_center=service_center,
        )
        .values("service_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    stats_labels = [stat["service_type__name"] for stat in service_stats]
    stats_data = [stat["count"] for stat in service_stats]

    status_stats = (
        Appointment.objects.filter(service_center=service_center)
        .values("status")
        .annotate(count=Count("id"))
    )

    weekday_stats = (
        Appointment.objects.filter(
            scheduled_date__gte=start_date, service_center=service_center
        )
        .annotate(weekday=ExtractWeekDay("scheduled_date"))
        .values("weekday")
        .annotate(count=Count("id"))
        .order_by("weekday")
    )

    weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    weekday_labels = []
    weekday_data = []
    for stat in weekday_stats:
        weekday_index = (int(stat["weekday"]) - 2) % 7
        weekday_labels.append(weekday_names[weekday_index])
        weekday_data.append(stat["count"])

    try:
        working_hours = WorkingHours.objects.get(day_of_week=selected_date.isoweekday())
    except WorkingHours.DoesNotExist:
        working_hours = None

    todays_schedule = []
    if working_hours and working_hours.is_working:
        all_slots = generate_time_slots(
            working_hours.start_time, working_hours.end_time
        )

        now = timezone.localtime(timezone.now())
        if selected_date == now.date():
            all_slots = [
                s
                for s in all_slots
                if datetime.strptime(s, "%H:%M").time()
                > (now + timedelta(minutes=0)).time()
            ]

        day_appointments = (
            Appointment.objects.filter(
                scheduled_date=selected_date,
                service_center=service_center,
                status__in=["SCHEDULED", "IN_PROGRESS"],
            )
            .select_related("car", "service_type", "car__owner")
            .order_by("scheduled_time")
        )

        last_app_id = None
        for slot in all_slots:
            slot_time = datetime.strptime(slot, "%H:%M").time()
            matched = None
            for a in day_appointments:
                end_t = a.end_time
                if not end_t and a.service_type and a.service_type.duration:
                    end_t = (
                        datetime.combine(selected_date, a.scheduled_time)
                        + timedelta(minutes=a.service_type.duration)
                    ).time()
                if not end_t:
                    end_t = a.scheduled_time

                if a.scheduled_time <= slot_time < end_t:
                    matched = a
                    break
            if matched:
                if str(matched.id) != str(last_app_id):
                    end_t = matched.end_time
                    if (
                        not end_t
                        and matched.service_type
                        and matched.service_type.duration
                    ):
                        end_t = (
                            datetime.combine(selected_date, matched.scheduled_time)
                            + timedelta(minutes=matched.service_type.duration)
                        ).time()
                    if not end_t:
                        end_t = matched.scheduled_time
                    todays_schedule.append(
                        {
                            "busy": True,
                            "start": matched.scheduled_time.strftime("%H:%M"),
                            "end": end_t.strftime("%H:%M"),
                            "title": f"{matched.service_type.name} — {matched.car}",
                            "status": matched.status,
                            "appointment_id": str(matched.id),
                        }
                    )
                    last_app_id = str(matched.id)
            else:
                todays_schedule.append({"time": slot, "busy": False})

    if period == "month":
        chart_start = today - timedelta(days=29)
    else:
        chart_start = today - timedelta(days=6)

    visits_qs = (
        Appointment.objects.filter(
            scheduled_date__gte=chart_start,
            scheduled_date__lte=today,
            service_center=service_center,
        )
        .values("scheduled_date")
        .annotate(count=Count("id"))
        .order_by("scheduled_date")
    )
    visits_labels = []
    visits_data = []
    current = chart_start
    while current <= today:
        visits_labels.append(current.strftime("%d.%m"))
        found = next((v for v in visits_qs if v["scheduled_date"] == current), None)
        visits_data.append(found["count"] if found else 0)
        current += timedelta(days=1)

    status_label_map = {k: v for k, v in Appointment.STATUS_CHOICES}
    status_stats_list = [
        {
            "status": s["status"],
            "count": s["count"],
            "label": status_label_map.get(s["status"], s["status"]),
        }
        for s in status_stats
    ]

    status_total = sum(s["count"] for s in status_stats)
    has_service_stats = any(stats_data) if stats_data else False
    has_weekday_stats = any(weekday_data) if weekday_data else False
    has_visits_data = any(visits_data) if visits_data else False

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "visits_labels": visits_labels,
                "visits_data": visits_data,
            }
        )

    context = {
        "service_center": service_center,
        "calendar_events": json.dumps(calendar_events, ensure_ascii=False),
        "stats_labels": json.dumps(stats_labels, ensure_ascii=False),
        "stats_data": json.dumps(stats_data, ensure_ascii=False),
        "weekday_labels": json.dumps(weekday_labels, ensure_ascii=False),
        "weekday_data": json.dumps(weekday_data, ensure_ascii=False),
        "status_stats": status_stats_list,
        "current_year": year,
        "current_month": month,
        "selected_date": selected_date.isoformat(),
        "todays_schedule": todays_schedule,
        "period": period,
        "visits_labels": json.dumps(visits_labels, ensure_ascii=False),
        "visits_data": json.dumps(visits_data, ensure_ascii=False),
        "has_service_stats": has_service_stats,
        "has_weekday_stats": has_weekday_stats,
        "has_visits_data": has_visits_data,
        "status_total": status_total,
    }
    return render(request, "admin_panel/admin_service_center_detail.html", context)


@login_required
@admin_required
def admin_service_center_edit(request, service_center_id):
    """Редактирование информации об автосервисе"""
    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    if request.method == "POST":
        form = ServiceCenterEditForm(
            request.POST, request.FILES, instance=service_center
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Информация о филиале обновлена")
            return redirect(
                "admin_panel:admin_service_center_detail",
                service_center_id=service_center.id,
            )
    else:
        form = ServiceCenterEditForm(instance=service_center)

    return render(
        request,
        "admin_panel/admin_service_center_edit.html",
        {"form": form, "service_center": service_center},
    )


@login_required
@admin_required
def admin_api_day_schedule(request, service_center_id):
    """JSON: расписание по слотам для выбранного дня"""
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse({"error": "Missing date"}, status=400)
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)

    service_center = get_object_or_404(ServiceCenter, id=service_center_id)

    try:
        working_hours = WorkingHours.objects.get(day_of_week=selected_date.isoweekday())
    except WorkingHours.DoesNotExist:
        return JsonResponse({"slots": []})

    if not working_hours.is_working:
        return JsonResponse({"slots": []})

    all_slots = generate_time_slots(working_hours.start_time, working_hours.end_time)
    now = timezone.localtime(timezone.now())
    if selected_date == now.date():
        all_slots = [
            s
            for s in all_slots
            if datetime.strptime(s, "%H:%M").time()
            > (now + timedelta(minutes=0)).time()
        ]

    day_appointments = (
        Appointment.objects.filter(
            scheduled_date=selected_date,
            service_center=service_center,
            status__in=["SCHEDULED", "IN_PROGRESS"],
        )
        .select_related("car", "service_type", "car__owner")
        .order_by("scheduled_time")
    )

    slots = []
    last_app_id = None
    for slot in all_slots:
        slot_time = datetime.strptime(slot, "%H:%M").time()
        matched = None
        for a in day_appointments:
            end_t = a.end_time
            if not end_t and a.service_type and a.service_type.duration:
                end_t = (
                    datetime.combine(selected_date, a.scheduled_time)
                    + timedelta(minutes=a.service_type.duration)
                ).time()
            if not end_t:
                end_t = a.scheduled_time

            if a.scheduled_time <= slot_time < end_t:
                matched = a
                break
        if matched:
            if str(matched.id) != str(last_app_id):
                end_t = matched.end_time
                if not end_t and matched.service_type and matched.service_type.duration:
                    end_t = (
                        datetime.combine(selected_date, matched.scheduled_time)
                        + timedelta(minutes=matched.service_type.duration)
                    ).time()
                if not end_t:
                    end_t = matched.scheduled_time
                slots.append(
                    {
                        "busy": True,
                        "start": matched.scheduled_time.strftime("%H:%M"),
                        "end": end_t.strftime("%H:%M"),
                        "title": f"{matched.service_type.name} — {matched.car}",
                        "status": matched.status,
                        "appointment_id": str(matched.id),
                    }
                )
                last_app_id = str(matched.id)
        else:
            slots.append({"time": slot, "busy": False})

    return JsonResponse({"slots": slots})


@login_required
@admin_required
def admin_appointment_detail(request, appointment_id):
    """Детальная информация о записи"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Appointment.STATUS_CHOICES):
            appointment.status = new_status
            appointment.save()
            messages.success(request, "Статус записи обновлен!")

    context = {
        "appointment": appointment,
        "status_choices": Appointment.STATUS_CHOICES,
    }
    return render(request, "admin_panel/admin_appointment_detail.html", context)


@login_required
@admin_required
def admin_api_appointments(request):
    """API для получения записей (для календаря)"""
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    service_center_id = request.GET.get("service_center")

    appointments = Appointment.objects.all()

    if start_date:
        appointments = appointments.filter(scheduled_date__gte=start_date)
    if end_date:
        appointments = appointments.filter(scheduled_date__lte=end_date)
    if service_center_id:
        appointments = appointments.filter(service_center_id=service_center_id)

    events = []
    for appointment in appointments:
        events.append(
            {
                "id": str(appointment.id),
                "title": f"{appointment.car} - {appointment.service_type.name}",
                "start": f"{appointment.scheduled_date}T{appointment.scheduled_time}",
                "end": (
                    f"{appointment.scheduled_date}T{appointment.end_time}"
                    if appointment.end_time
                    else f"{appointment.scheduled_date}T{appointment.scheduled_time}"
                ),
                "status": appointment.status,
                "user": appointment.car.owner.get_full_name()
                or appointment.car.owner.username,
                "className": f"appointment-status-{appointment.status.lower()}",
            }
        )

    return JsonResponse(events, safe=False)


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_branches(request):
    """Список филиалов (автосервисов) в виде карточек с фото"""
    service_centers = ServiceCenter.objects.all().annotate(
        appointments_count=Count("appointment", distinct=False)
    )
    return render(
        request,
        "admin_panel/admin_branches.html",
        {"service_centers": service_centers},
    )
