from django.contrib import admin
from .models import *

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    search_fields = ('name', 'parent__name')
    list_display = ('name', 'parent', "vector", "get_vehicle")
    raw_id_fields = ('vector',)

    def get_vehicle(self, obj):
        if hasattr(obj, "vector") and obj.vector:
            if hasattr(obj.vector, "vehicle") and obj.vector.vehicle:
                return obj.vector.vehicle
        return None
    get_vehicle.short_description = "Vehicle"

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('name', )
    

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    pass
