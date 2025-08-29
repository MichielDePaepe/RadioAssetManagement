from django.contrib import admin
from .models import Ticket, TicketMessage

class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1
    readonly_fields = ('created_at', )

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'radio', 'title', 'status', 'created_at', 'astrid_ticket', 'siamu_ticket')
    search_fields = ('title', 'description', 'astrid_ticket', 'siamu_ticket', 'radio__TEI')
    list_filter = ('status', 'created_at')
    raw_id_fields = ('radio', )
    readonly_fields = ('created_at', )
    inlines = [TicketMessageInline]