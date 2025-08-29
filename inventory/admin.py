from django.contrib import admin
from .models import *
from organization.models import *
from rangefilter.filters import DateRangeFilter


# class PostFilter(admin.SimpleListFilter):
#     title = 'Post'
#     parameter_name = 'post'

#     def lookups(self, request, model_admin):
#         return [(post.id, post.name) for post in Post.objects.all()]

#     def queryset(self, request, queryset):
#         if self.value():
#             return queryset.filter(inventory__container__team__post_id=self.value())
#         return queryset



@admin.register(InventoryEntry)
class InventoryEntryAdmin(admin.ModelAdmin):
    list_display = ('radio', 'container', 'timestamp', 'get_tei', 'get_issi')
    raw_id_fields = ('radio', )
    list_filter = (
        ('timestamp', DateRangeFilter),
    )

    def get_tei(self, obj):
        return str(obj.radio.TEI).zfill(14)
    get_tei.short_description = 'TEI'

    def get_issi(self, obj):
        return str(obj.radio.ISSI).zfill(7)
    get_issi.short_description = 'ISSI'

