from django.contrib import admin
from .models import *

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    search_fields = ('name', 'parent__name')
    list_display = ('name', 'parent', "show_in_listing")

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('name', )
    

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    pass

@admin.register(RadioContainerLink)
class RadioContainerLinkAdmin(admin.ModelAdmin):
    raw_id_fields = ('radio',)
    list_display = ('name', 'container', 'radio', 'get_issi', 'get_alias', 'temporary')
    search_fields = ('name', 'container__name', 'radio__TEI', 'radio__subscription__issi__number', 'radio__subscription__issi__alias')
    readonly_fields = ('updated_at',)



    def get_alias(self, obj):
        return obj.radio.subscription.issi.alias if hasattr(obj.radio, 'subscription') else None
    get_alias.short_description = 'Alias'

    def get_issi(self, obj):
        return obj.radio.subscription.issi.number if hasattr(obj.radio, 'subscription') else None
    get_issi.short_description = 'ISSI'