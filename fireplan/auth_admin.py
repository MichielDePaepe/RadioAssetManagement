# fireplan/auth_admin.py
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from .auth_models import (
    FireplanLanguage,
    FireplanGrade,
    FireplanGroup,
    FireplanSubGroup,
    FireplanFiliere,
    FireplanProfile,
)


# @admin.register(FireplanLanguage)
class FireplanLanguageAdmin(admin.ModelAdmin):
    list_display = ("code", "label")
    search_fields = ("code", "label")


@admin.register(FireplanGrade)
class FireplanGradeAdmin(TranslationAdmin):
    list_display = ("name", "abbrev")
    search_fields = ("name", "abbrev")
    # With modeltranslation, this will expose name_xx / abbrev_xx in the form


# @admin.register(FireplanGroup)
class FireplanGroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


# @admin.register(FireplanSubGroup)
class FireplanSubGroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


# @admin.register(FireplanFiliere)
class FireplanFiliereAdmin(admin.ModelAdmin):
    list_display = ("code",)
    search_fields = ("code",)


@admin.register(FireplanProfile)
class FireplanProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "fireplan_username",
        "language",
        "grade",
        "groups",
        "subgroups",
        "filiere",
    )
    list_select_related = ("user", "language", "grade", "groups", "subgroups", "filiere")
    search_fields = (
        "fireplan_username",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )
    list_filter = ("language", "grade", "groups", "subgroups", "filiere")
