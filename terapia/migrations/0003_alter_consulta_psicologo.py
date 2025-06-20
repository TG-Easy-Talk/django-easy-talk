# Generated by Django 5.1.8 on 2025-06-05 20:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terapia', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='consulta',
            name='psicologo',
            field=models.ForeignKey(limit_choices_to=models.Q(('valor_consulta__isnull', False), ('especializacoes__isnull', False), ('disponibilidade__isnull', False)), on_delete=django.db.models.deletion.CASCADE, related_name='consultas', to='terapia.psicologo'),
        ),
    ]
