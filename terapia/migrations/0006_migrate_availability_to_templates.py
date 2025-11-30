from django.db import migrations
from django.utils import timezone

def migrate_availability(apps, schema_editor):
    IntervaloDisponibilidade = apps.get_model('terapia', 'IntervaloDisponibilidade')
    IntervaloDisponibilidadeTemplate = apps.get_model('terapia', 'IntervaloDisponibilidadeTemplate')
    
    templates = []
    for intervalo in IntervaloDisponibilidade.objects.all():
        # Convert data_hora_inicio/fim to local time to extract day of week and time
        # Assuming the existing data represents the recurring schedule
        
        # Note: In the old model, data_hora_inicio was a DateTime in 2024.
        # We need to extract the weekday and time from it.
        # We use timezone.localtime to respect the server's configured timezone logic
        # or the datetime's own timezone info.
        
        start_local = timezone.localtime(intervalo.data_hora_inicio)
        end_local = timezone.localtime(intervalo.data_hora_fim)
        
        template = IntervaloDisponibilidadeTemplate(
            psicologo=intervalo.psicologo,
            dia_semana_inicio_iso=start_local.isoweekday(),
            hora_inicio=start_local.time(),
            dia_semana_fim_iso=end_local.isoweekday(),
            hora_fim=end_local.time(),
        )
        templates.append(template)
    
    if templates:
        IntervaloDisponibilidadeTemplate.objects.bulk_create(templates)

def reverse_migration(apps, schema_editor):
    IntervaloDisponibilidadeTemplate = apps.get_model('terapia', 'IntervaloDisponibilidadeTemplate')
    IntervaloDisponibilidadeTemplate.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('terapia', '0005_add_hybrid_availability_models'),
    ]

    operations = [
        migrations.RunPython(migrate_availability, reverse_migration),
    ]
