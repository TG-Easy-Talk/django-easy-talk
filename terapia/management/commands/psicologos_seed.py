import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from terapia.models import Psicologo, Especializacao

class Command(BaseCommand):
    help = 'Seeds the database with psychologists from a JSON file'

    def handle(self, *args, **options):
        json_path = os.path.join(settings.BASE_DIR, 'terapia', 'fixtures', 'psicologos_seed.json')
        
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'Seed file not found at {json_path}'))
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            psicologos_data = json.load(f)

        User = get_user_model()
        
        for data in psicologos_data:
            email = data['email']
            
            # Create or get User
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    email=email,
                    password='password123' # Default password
                )
                self.stdout.write(self.style.SUCCESS(f'User {email} created'))
            else:
                user = User.objects.get(email=email)
                self.stdout.write(self.style.WARNING(f'User {email} already exists'))

            # Create or get Psicologo
            if not Psicologo.objects.filter(crp=data['crp']).exists():
                psicologo = Psicologo.objects.create(
                    usuario=user,
                    nome_completo=data['nome_completo'],
                    crp=data['crp'],
                    sobre_mim=data['sobre_mim'],
                    valor_consulta=data['valor_consulta'],
                    foto=data['foto']
                )
                
                # Add specializations
                for spec_name in data['especializacoes']:
                    spec, created = Especializacao.objects.get_or_create(
                        titulo=spec_name,
                        defaults={'descricao': f'Especialização em {spec_name}'}
                    )
                    psicologo.especializacoes.add(spec)
                
                # Add availability
                if 'disponibilidade' in data:
                    from terapia.models import IntervaloDisponibilidade
                    from datetime import datetime
                    from django.utils import timezone
                    
                    for slot in data['disponibilidade']:
                        start_time = datetime.strptime(slot['inicio'], '%H:%M').time()
                        end_time = datetime.strptime(slot['fim'], '%H:%M').time()
                        
                        IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                            dia_semana_inicio_iso=slot['dia'],
                            hora_inicio=start_time,
                            dia_semana_fim_iso=slot['dia'],
                            hora_fim=end_time,
                            fuso=timezone.get_current_timezone(),
                            psicologo=psicologo
                        )
                else:
                    # Fallback default
                    from terapia.models import IntervaloDisponibilidade
                    from datetime import time
                    from django.utils import timezone
                    
                    IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                        dia_semana_inicio_iso=1, # Monday
                        hora_inicio=time(8, 0),
                        dia_semana_fim_iso=1, # Monday
                        hora_fim=time(18, 0),
                        fuso=timezone.get_current_timezone(),
                        psicologo=psicologo
                    )

                self.stdout.write(self.style.SUCCESS(f'Psicologo {data["nome_completo"]} created with availability'))
            else:
                # Ensure existing seeded psychologists have availability and correct photo
                psicologo = Psicologo.objects.get(crp=data['crp'])
                
                # Update photo if changed
                if psicologo.foto.name != data['foto']:
                    psicologo.foto = data['foto']
                    psicologo.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated photo for Psicologo {data["nome_completo"]}'))

                # Update name if changed
                if psicologo.nome_completo != data['nome_completo']:
                    old_name = psicologo.nome_completo
                    psicologo.nome_completo = data['nome_completo']
                    psicologo.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated name for Psicologo {old_name} to {data["nome_completo"]}'))

                # Update description if changed
                if psicologo.sobre_mim != data['sobre_mim']:
                    psicologo.sobre_mim = data['sobre_mim']
                    psicologo.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated description for Psicologo {data["nome_completo"]}'))

                # Update specializations
                current_specs = set(psicologo.especializacoes.values_list('titulo', flat=True))
                new_specs = set(data['especializacoes'])
                
                if current_specs != new_specs:
                    psicologo.especializacoes.clear()
                    for spec_name in data['especializacoes']:
                        spec, created = Especializacao.objects.get_or_create(
                            titulo=spec_name,
                            defaults={'descricao': f'Especialização em {spec_name}'}
                        )
                        psicologo.especializacoes.add(spec)
                    self.stdout.write(self.style.SUCCESS(f'Updated specializations for Psicologo {data["nome_completo"]}'))

                # Update availability
                if 'disponibilidade' in data:
                    # Clear existing availability
                    psicologo.disponibilidade.all().delete()
                    
                    from terapia.models import IntervaloDisponibilidade
                    from datetime import datetime
                    from django.utils import timezone
                    
                    for slot in data['disponibilidade']:
                        start_time = datetime.strptime(slot['inicio'], '%H:%M').time()
                        end_time = datetime.strptime(slot['fim'], '%H:%M').time()
                        
                        IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                            dia_semana_inicio_iso=slot['dia'],
                            hora_inicio=start_time,
                            dia_semana_fim_iso=slot['dia'],
                            hora_fim=end_time,
                            fuso=timezone.get_current_timezone(),
                            psicologo=psicologo
                        )
                    self.stdout.write(self.style.SUCCESS(f'Updated availability for Psicologo {data["nome_completo"]}'))
