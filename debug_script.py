import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'easy_talk.settings')
django.setup()

from terapia.models import Consulta, Paciente, Psicologo
from django.contrib.auth import get_user_model

User = get_user_model()

try:
    # Create dummy user/paciente/psicologo
    if not User.objects.filter(email='p1@example.com').exists():
        u1 = User.objects.create_user('p1@example.com', 'pass')
        p1 = Paciente.objects.create(usuario=u1, nome='P1', cpf='11111111111')
    else:
        p1 = User.objects.get(email='p1@example.com').paciente

    if not User.objects.filter(email='psi1@example.com').exists():
        u2 = User.objects.create_user('psi1@example.com', 'pass')
        psi1 = Psicologo.objects.create(usuario=u2, nome_completo='Psi1', crp='12345')
    else:
        psi1 = User.objects.get(email='psi1@example.com').psicologo

    data_hora = timezone.now() + timedelta(days=1)
    c = Consulta(data_hora_agendada=data_hora)
    c.paciente = p1
    c.psicologo = psi1
    print(f"Saving with {c.data_hora_agendada}")
    c.save()
    print("Saved")
except Exception as e:
    print(f"Error: {e}")
