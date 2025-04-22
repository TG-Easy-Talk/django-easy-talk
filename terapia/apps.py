from django.apps import AppConfig


class TerapiaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'terapia'
    verbose_name = 'Terapia'

    @staticmethod
    def ready():
        import terapia.signals
