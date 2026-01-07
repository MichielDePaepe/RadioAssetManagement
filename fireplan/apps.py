from django.apps import AppConfig


class FireplanConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fireplan'

    def ready(self):
        import fireplan.signals

