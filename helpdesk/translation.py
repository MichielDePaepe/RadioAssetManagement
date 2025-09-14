from modeltranslation.translator import translator, TranslationOptions
from .models import TicketType, TicketStatus

class TicketTypeTranslationOptions(TranslationOptions):
    fields = ('name',)

class TicketStatusTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(TicketType, TicketTypeTranslationOptions)
translator.register(TicketStatus, TicketStatusTranslationOptions)
