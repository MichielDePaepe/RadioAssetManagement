# fireplan/translation.py

from modeltranslation.translator import TranslationOptions, translator
from .models import StatusCode


class StatusCodeTranslationOptions(TranslationOptions):
    fields = ("description",)


translator.register(StatusCode, StatusCodeTranslationOptions)
