from django.apps import AppConfig
from django.db.models.signals import post_migrate

def run_seed(sender, **kwargs):
    from django.core.management import call_command
    call_command('seed_psicologos')

class TerapiaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'terapia'

    def ready(self):
        post_migrate.connect(run_seed, sender=self)
    verbose_name = 'Terapia'
