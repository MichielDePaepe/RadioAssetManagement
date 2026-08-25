from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import *


class RadioPositionAssignmentInline(admin.TabularInline):
    model = RadioPositionAssignment
    extra = 0
    fields = ("role", "radio", "assigned_at", "ended_at", "replaces", "created_by", "note")
    readonly_fields = ("assigned_at",)
    autocomplete_fields = ("radio", "replaces", "created_by")
    show_change_link = True


class RadioPositionInline(admin.TabularInline):
    model = RadioPosition
    extra = 0
    fields = ("name", "order", "active")
    show_change_link = True


def radio_detail_link(radio):
    url = reverse("radio:detail", kwargs={"pk": radio.pk})
    return format_html('<a href="{}">{}</a>', url, radio.inventory_label)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "location_type", "service", "parent", "active")
    list_filter = ("location_type", "active")
    search_fields = ("name", "service__code", "service__description", "parent__name")
    autocomplete_fields = ("service", "parent")
    filter_horizontal = ("dashboard_vectors", "dashboard_locations")
    fieldsets = (
        (None, {
            "fields": ("name", "location_type", "service", "parent", "active"),
        }),
        ("Dashboard", {
            "fields": ("dashboard_vectors", "dashboard_locations"),
        }),
    )
    inlines = (RadioPositionInline,)


@admin.register(RadioPosition)
class RadioPositionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "parent_label",
        "active",
        "active_primary_radio",
        "active_substitute_radio",
        "operational_radio",
    )
    list_filter = ("active",)
    search_fields = (
        "name",
        "vector__resourceCode",
        "vector__name",
        "vehicle__number",
        "vehicle__call_sign",
        "location__name",
    )
    autocomplete_fields = ("vector", "vehicle", "location")
    inlines = (RadioPositionAssignmentInline,)

    def active_primary_radio(self, obj):
        assignment = obj.active_primary
        return radio_detail_link(assignment.radio) if assignment else None

    def active_substitute_radio(self, obj):
        assignment = obj.active_substitute
        return radio_detail_link(assignment.radio) if assignment else None

    def operational_radio(self, obj):
        assignment = obj.operational_assignment
        return radio_detail_link(assignment.radio) if assignment else None


@admin.register(RadioPositionAssignment)
class RadioPositionAssignmentAdmin(admin.ModelAdmin):
    list_display = ("radio_label", "position", "role", "assigned_at", "ended_at", "replaces_label", "is_active")
    list_filter = ("role", "ended_at")
    search_fields = (
        "radio__TEI",
        "radio__subscription__issi__number",
        "radio__subscription__issi__alias",
        "position__name",
        "position__location__name",
        "position__vehicle__number",
        "position__vector__name",
    )
    autocomplete_fields = ("radio", "position", "replaces", "created_by")
    date_hierarchy = "assigned_at"

    def radio_label(self, obj):
        return radio_detail_link(obj.radio)

    radio_label.short_description = "Radio"
    radio_label.admin_order_field = "radio__subscription__issi__alias"

    def replaces_label(self, obj):
        return radio_detail_link(obj.replaces.radio) if obj.replaces else None

    replaces_label.short_description = "Replaces"

    def is_active(self, obj):
        return obj.ended_at is None

    is_active.boolean = True
