from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import *



class TicketLogInline(admin.TabularInline):
    model = TicketLog
    extra = 0
    readonly_fields = ("timestamp", "user", "status_before")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "radio", "ticket_type", "status", "priority", 
        "created_at", "updated_at", "created_by", "assigned_to"
    )
    list_filter = ("status", "priority", "ticket_type")
    search_fields = ("title", "description", "radio__TEI", "radio__serial_number", "siamu_ticket")
    raw_id_fields = ("radio",)
    inlines = [TicketLogInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj: 
            return ("radio", "status", "created_at", "updated_at", "created_by")
        return ("status", )


@admin.register(TicketType)
class TicketTypeAdmin(TranslationAdmin):
    list_display = ('name', "code")
    search_fields = ("name", "code")

@admin.register(TicketStatus)
class TicketStatusAdmin(TranslationAdmin):
    list_display = ('name', "code")
    search_fields = ("name", "code")
