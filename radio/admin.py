from django.utils.html import format_html
from django.contrib import admin
from django.db.models import Q

from .models import *


class HasSubscriptionFilter(admin.SimpleListFilter):
    title = 'has subscription'
    parameter_name = 'has_subscription'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(subscription__isnull=False).distinct()
        elif self.value() == 'no':
            return queryset.filter(subscription__isnull=True)
        return queryset


class RadioOwnerFilter(admin.SimpleListFilter):
    title = 'owner'
    parameter_name = 'owner'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(
                Q(subscription__issi__customer__owner=True) |
                Q(subscription__isnull=True)
            )
        elif self.value() == 'no':
            return queryset.filter(
                (
                    Q(subscription__issi__customer__owner=False) |
                    Q(subscription__issi__customer__isnull=True)
                ) &
                Q(subscription__isnull=False)
            )
        return queryset

class ISSIOwnerFilter(admin.SimpleListFilter):
    title = 'owner'
    parameter_name = 'owner'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(customer__owner=True)
        elif self.value() == 'no':
            return queryset.filter(
                Q(customer__owner=False) |
                Q(customer__isnull=True)
            )
        return queryset






@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('get_tei', 'get_issi', 'astrid_alias', 'get_alias', 'active')
    search_fields = ('radio__TEI', 'issi__number')
    raw_id_fields = ('radio', 'issi')

    def get_tei(self, obj):
        return str(obj.radio.TEI).zfill(14)
    get_tei.short_description = 'TEI'

    def get_issi(self, obj):
        return str(obj.issi.number).zfill(7)
    get_issi.short_description = 'ISSI'

    def get_alias(self, obj):
        return obj.issi.alias
    get_alias.short_description = 'Alias'



@admin.register(Radio)
class RadioAdmin(admin.ModelAdmin):
    list_display = ('get_tei', 'model', 'get_issi_list', 'get_alias_list', 'is_active', 'fireplan_id')
    search_fields = (
        'TEI', 
        'subscription__issi__number',
        'subscription__issi__alias'
    )
    list_filter = ('model', RadioOwnerFilter, HasSubscriptionFilter,)
    readonly_fields = ('model', )

    def get_tei(self, obj):
        return format_html('<span style="font-family: monospace;">{}</span>', str(obj.TEI).zfill(14))
    get_tei.short_description = 'TEI'

    def get_issi_list(self, obj):
        return str(obj.subscription.issi.number).zfill(7) if hasattr(obj, 'subscription') else "-"
    get_issi_list.short_description = 'ISSI'

    def get_alias_list(self, obj):
        return obj.subscription.issi.alias if hasattr(obj, 'subscription') and obj.subscription.issi.alias else "-"
    get_alias_list.short_description = 'Alias'

    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'



@admin.register(RadioModel)
class RadioTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_atex')


@admin.register(TEIRange)
class TEIRangeAdmin(admin.ModelAdmin):
    list_display = ('model', 'formatted_min_tei', 'formatted_max_tei')
    search_fields = ('model__name',)  # optioneel

    def get_search_results(self, request, queryset, search_term):
        if search_term.isdigit():
            tei = int(search_term)
            queryset = queryset.filter(min_tei__lte=tei, max_tei__gte=tei)
            return queryset, False
        return super().get_search_results(request, queryset, search_term)

    def formatted_min_tei(self, obj):
        return format_html('<span style="font-family: monospace;">{}</span>', str(obj.min_tei).zfill(14))
    formatted_min_tei.short_description = 'Min TEI'

    def formatted_max_tei(self, obj):
        return format_html('<span style="font-family: monospace;">{}</span>', str(obj.max_tei).zfill(14))
    formatted_max_tei.short_description = 'Max TEI'




@admin.register(ISSI)
class ISSIAdmin(admin.ModelAdmin):
    list_display = ('number', 'alias')#, 'has_subscription')
    search_fields = ('number', 'alias')
    list_filter = (ISSIOwnerFilter, HasSubscriptionFilter,)
    readonly_fields = ('customer', 'discipline')

    def has_subscription(self, obj):
        return obj.subscription.exists()
    has_subscription.boolean = True
    has_subscription.short_description = 'Has subscription'



#@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    pass


#@admin.register(ISSICustomerRange)
class ISSICustomerRangeAdmin(admin.ModelAdmin):
    list_display = ('customer', 'min_issi', 'max_issi')


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    pass


#@admin.register(ISSIDisciplineRange)
class ISSIDisciplineRangeAdmin(admin.ModelAdmin):
    list_display = ('discipline', 'min_issi', 'max_issi')

