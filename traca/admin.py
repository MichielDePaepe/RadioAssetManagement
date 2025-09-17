from django.contrib import admin
from .models import *


@admin.register(Cabinet)
class CabinetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location")
    search_fields = ("name", "location")
    ordering = ("name",)


@admin.register(CabinetSlot)
class CabinetSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "cabinet", "radio", "state")
    list_filter = ("cabinet", "state")
    search_fields = ("name", "radio__TEI", "radio__serial_number")
    raw_id_fields = ("radio",)
    ordering = ("cabinet", "name")


class CabinetLogInline(admin.TabularInline):
    model = CabinetLog
    extra = 0
    readonly_fields = ("timestamp",)
    raw_id_fields = ("radio_in", "radio_out", "user")


@admin.register(CabinetLog)
class CabinetLogAdmin(admin.ModelAdmin):
    list_display = ("id", "slot", "type", "radio_in", "radio_out", "user", "timestamp")
    list_filter = ("type", "slot__cabinet")
    search_fields = (
        "slot__name",
        "slot__cabinet__name",
        "radio_in__TEI",
        "radio_in__serial_number",
        "radio_out__TEI",
        "radio_out__serial_number",
        "user__username",
    )
    raw_id_fields = ("slot", "radio_in", "radio_out", "user")
    ordering = ("-timestamp",)
