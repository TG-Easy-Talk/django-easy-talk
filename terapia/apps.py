from django.apps import AppConfig
from django.db.models.signals import post_migrate
from .popular_banco import funcoes_de_popular


class TerapiaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'terapia'
    verbose_name = 'Terapia'

    def ready(self):
        import terapia.signals

        for funcao in funcoes_de_popular:
            post_migrate.connect(funcao, sender=self)
