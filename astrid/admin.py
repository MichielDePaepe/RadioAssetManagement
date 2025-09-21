from django.contrib import admin
from .models import *
from helpdesk.admin import TicketLogInline


@admin.action(description="Mark selected requests as in progress")
def make_in_progress(modeladmin, request, queryset):
    for req in queryset:
        req.start_execution(user=request.user)

@admin.action(description="Mark selected requests as waiting for verification")
def make_waiting_verification(modeladmin, request, queryset):
    for req in queryset:
        req.mark_waiting_verification(user=request.user)

@admin.action(description="Mark selected requests as done")
def make_done(modeladmin, request, queryset):
    for req in queryset:
        req.mark_done(user=request.user)


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "request_type",
        "old_radio",
        "radio",
        "old_issi",
        "new_issi",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("request_type", "status", "priority")
    search_fields = (
        "radio__tei",
        "old_radio__tei",
        "radio__alias",
        "old_radio__alias",
        "new_issi__issi",
        "old_issi__issi",
        "external_reference",
    )
    raw_id_fields = ("radio", "old_radio", "new_issi", "old_issi")

    inlines = [TicketLogInline]

    readonly_fields = ("ticket_type",)

    exclude = ("title", "created_by")

    actions = [make_in_progress, make_waiting_verification, make_done]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + (
                "status",
                "created_at",
                "updated_at",
                "created_by",
            )
        return self.readonly_fields + ("status",)
