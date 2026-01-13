# fireplan/admin.py

from __future__ import annotations

from django.contrib import admin, messages
from .models import *
from .sync import sync_fireplan_fleet, sync_vectors

from .auth_admin import *
from .sync_inventory import sync_closed_inventories_portable_radio_teis


@admin.action(description="Sync inventories (incremental)")
def sync_inventories_incremental(modeladmin, request, queryset):
    inserted = sync_closed_inventories_portable_radio_teis(full_sync=False)
    messages.success(request, f"Inserted inventories: {inserted}")


@admin.action(description="Sync inventories (FULL)")
def sync_inventories_full(modeladmin, request, queryset):
    inserted = sync_closed_inventories_portable_radio_teis(full_sync=True)
    messages.success(request, f"Inserted inventories: {inserted}")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "utilisation",
        "status",
        "radio"
    )
    list_filter = ("status",)
    search_fields = ("number", "plate", "id", "chassis", "radio__subscription__issi__number")
    raw_id_fields = ("radio", )
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

class FireplanInventoryRadioInline(admin.TabularInline):
    model = FireplanInventoryRadio
    extra = 0
    fields = ("tei", "radio")
    autocomplete_fields = ("radio",)
    readonly_fields = ()
    show_change_link = True


@admin.register(FireplanInventory)
class FireplanInventoryAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle_alpha_code",
        "closed_at",
        "done_by_full_name",
    )
    ordering = ("-closed_at",)
    search_fields = (
        "vehicle_alpha_code",
        "done_by_full_name",
        "uuid",
    )
    inlines = [FireplanInventoryRadioInline]
    actions = [sync_inventories_incremental, sync_inventories_full]


@admin.register(FireplanInventoryRadio)
class FireplanInventoryRadioAdmin(admin.ModelAdmin):
    list_display = (
        "inventory",
        "tei",
        "radio",
    )
    search_fields = (
        "tei",
        "inventory__vehicle_alpha_code",
        "inventory__uuid",
    )
    autocomplete_fields = ("inventory", "radio")
    ordering = ("-id",)