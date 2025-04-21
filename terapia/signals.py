from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Paciente, Psicologo

User = get_user_model()


@receiver(post_save, sender=User)
def create_paciente_profile(sender, instance, created, **kwargs):
    """
    Ao criar um User, gera automaticamente o Paciente associado.
    """
    if created:
        Paciente.objects.create(usuario=instance)  # :contentReference[oaicite:4]{index=4}


@receiver(post_save, sender=User)
def create_psicologo_profile(sender, instance, created, **kwargs):
    """
    Sempre que um User for criado e estiver associado
    ao grupo 'psicologos', cria um Psicologo.
    Ajuste a condição conforme sua lógica de perfil.
    """
    if created and instance.groups.filter(name='psicologos').exists():
        Psicologo.objects.create(usuario=instance)
