from django.contrib import admin
from .models import *


@admin.register(Cabinet)
class CabinetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location")
    search_fields = ("name", "location")
    ordering = ("name",)
