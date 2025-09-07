from django.contrib import admin
from .models import Printer

@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'ip', 'backend')
    list_filter = ('backend',)
    search_fields = ('name', 'location', 'ip')