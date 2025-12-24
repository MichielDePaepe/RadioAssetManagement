from organization.models import *
from rangefilter.filters import DateRangeFilter


from django.contrib import admin
from django.db.models import Q
from django.utils import timezone

from polymorphic.admin import (
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
)

from .models import *


# ---------- Inlines ----------

class RadioEndpointInline(admin.TabularInline):
    model = RadioEndpoint
    extra = 0
    fields = ("name", "allows_multiple", "primary_radio")
    autocomplete_fields = ("primary_radio",)
    show_change_link = True


class RadioAssignmentInline(admin.TabularInline):
    model = RadioAssignment
    extra = 0
    fields = ("radio", "reason", "start_at", "end_at", "ticket", "replaces_radio")
    readonly_fields = ("start_at",)
    autocomplete_fields = ("radio", "ticket", "replaces_radio")
    show_change_link = True

    def get_queryset(self, request):
        # Show newest first
        return super().get_queryset(request).order_by("-start_at")


# ---------- Container admin (polymorphic) ----------

@admin.register(VectorContainer)
class VectorContainerAdmin(PolymorphicChildModelAdmin):
    base_model = VectorContainer
    inlines = (RadioEndpointInline,)
    autocomplete_fields = ("vector",)
    list_display = ("label", "vector")
    search_fields = ("label", "vector__id", "vector__number", "vector__call_sign")  # adapt to your Vector fields


@admin.register(LocationContainer)
class LocationContainerAdmin(PolymorphicChildModelAdmin):
    base_model = LocationContainer
    inlines = (RadioEndpointInline,)
    list_display = ("label", "location_type")
    list_filter = ("location_type",)
    search_fields = ("label",)


@admin.register(RadioContainer)
class RadioContainerParentAdmin(PolymorphicParentModelAdmin):
    base_model = RadioContainer
    child_models = (VectorContainer, LocationContainer)
    list_display = ("label", "polymorphic_ctype")
    search_fields = ("label",)
    inlines = (RadioEndpointInline,)


# ---------- Endpoint admin ----------

@admin.register(RadioEndpoint)
class RadioEndpointAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "container",
        "primary_radio",
        "current_radio",
        "current_reason",
        "current_since",
    )
    list_filter = ("allows_multiple", "container__polymorphic_ctype")
    search_fields = ("name", "container__label", "primary_radio__subscription__issi__number")
    autocomplete_fields = ("container", "primary_radio")
    inlines = (RadioAssignmentInline,)
    readonly_fields = ("current_radio", "current_reason", "current_since")

    def _current_assignment(self, obj):
        return obj.current_assignment

    def current_radio(self, obj):
        a = self._current_assignment(obj)
        return a.radio if a else None

    def current_reason(self, obj):
        a = self._current_assignment(obj)
        return a.reason if a else None

    def current_since(self, obj):
        a = self._current_assignment(obj)
        return a.start_at if a else None

    current_radio.short_description = "Current radio"
    current_reason.short_description = "Current reason"
    current_since.short_description = "Current since"


# ---------- Assignment admin ----------

@admin.register(RadioAssignment)
class RadioAssignmentAdmin(admin.ModelAdmin):
    list_display = ("radio", "endpoint", "reason", "start_at", "end_at", "ticket", "replaces_radio", "is_open")
    list_filter = ("reason", "end_at")
    search_fields = ("radio__subscription__issi__number", "endpoint__name", "endpoint__container__label")
    autocomplete_fields = ("radio", "endpoint", "ticket", "replaces_radio")
    date_hierarchy = "start_at"

    def is_open(self, obj):
        return obj.end_at is None

    is_open.boolean = True
    is_open.short_description = "Open"

# ---------- Post admin ----------

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("label", "service")
    search_fields = ("label",)
    autocomplete_fields = ("service",)

