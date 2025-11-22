import os
import sys

from django.apps import AppConfig
from django.core.management import call_command
from django.db.models.signals import post_migrate


def run_seed_on_migrate(sender, **kwargs):
    call_command('psicologos_seed')


def run_seed_on_runserver():
    try:
        print("Running automatic seed...")
        call_command('psicologos_seed')
    except Exception as e:
        print(f"Error running automatic seed: {e}")


class TerapiaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'terapia'
    verbose_name = 'Terapia'

    def ready(self):
        """Initialize app: connect signals and run seed for development."""
        post_migrate.connect(run_seed_on_migrate, sender=self)

        is_runserver = 'runserver' in sys.argv
        is_reloader_process = os.environ.get('RUN_MAIN') == 'true'

        if is_runserver and is_reloader_process:
            run_seed_on_runserver()
