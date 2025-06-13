from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate
from .popular_banco import popular_tudo


class TerapiaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'terapia'
    verbose_name = 'Terapia'

    def ready(self):
        import terapia.signals

        if settings.DATABASES['default']['NAME'] != 'db.sqlite3':  # Substitua pelo nome do banco padrão
            return

        post_migrate.connect(popular_tudo, sender=self)
