# fireplan/translation.py

from modeltranslation.translator import register, TranslationOptions
from .models import StatusCode
from .auth_models import FireplanGrade


@register(StatusCode)
class StatusCodeTranslationOptions(TranslationOptions):
    fields = ("description",)

@register(FireplanGrade)
class FireplanGradeTranslationOptions(TranslationOptions):
    fields = ("name", "abbrev")
