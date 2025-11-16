from django.contrib import admin
from django.contrib import messages
from .models import *
from .sync import sync_fireplan_fleet, sync_vectors



@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "utilisation",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("number", "plate", "id", "chassis")
    readonly_fields = ("call_sign", )
    actions = ["sync_fireplan"]

    def sync_fireplan(self, request, queryset=None):
        count = sync_fireplan_fleet()
        self.message_user(
            request,
            f"Synchronisatie voltooid. {count} voertuigen bijgewerkt.",
            level=messages.SUCCESS,
        )

    sync_fireplan.short_description = "Synchroniseer Fireplan Fleet"



@admin.register(Vector)
class VectorAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle",
        "name",
        "abbreviation",
        "service",
        "resourceTypeCode",
        "status_with_color",   # <<< nieuwe kolom
    )

    list_filter = (
        "service",
        "resourceTypeCode",
        "statusCode",
    )

    search_fields = ("name", "abbreviation", "vehicle__number")

    readonly_fields = (
        "vehicle",
        "name",
        "abbreviation",
        "resourceCode",
        "service",
        "resourceTypeCode",
        "statusCode",
        "orderServiceAbbreviation",
    )

    actions = ["sync_vectors"]


    def status_with_color(self, obj):
        if not obj.statusCode:
            return "-"

        return obj.statusCode.as_html()
    status_with_color.short_description = "Status"
    status_with_color.allow_tags = True   # (nodig voor oudere Django, maar 4.x gebruikt format_html dus ok)


    def sync_vectors(self, request, queryset=None):
        count = sync_vectors()
        self.message_user(
            request,
            f"Synchronisatie vectoren voltooid. {count} vectoren gekoppeld aan voertuigen.",
            level=messages.SUCCESS,
        )
    sync_vectors.short_description = "Synchroniseer Vectors"



@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")


@admin.register(ResourceTypeCode)
class ResourceTypeCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")


@admin.register(StatusCode)
class StatusCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")
