# from django.db.models.signals import post_delete
# from django.dispatch import receiver
# from .models import Paciente, Psicologo


# @receiver(post_delete, sender=Paciente)
# def apaga_usuario_apos_excluir_paciente(sender, instance, **kwargs):
#     instance.usuario.delete()


# @receiver(post_delete, sender=Psicologo)
# def apaga_usuario_apos_excluir_psicologo(sender, instance, **kwargs):
#     instance.usuario.delete()
