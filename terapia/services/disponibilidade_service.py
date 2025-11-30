"""
Service layer for managing psychologist availability with hybrid architecture.

This service handles the logic for combining weekly templates with week-specific overrides.
"""

from datetime import timedelta, datetime
from django.utils import timezone
from terapia.models import (
    IntervaloDisponibilidadeTemplate,
    IntervaloDisponibilidadeOverride,
    SemanaDisponibilidadeConfig,
    IntervaloDisponibilidade,
)


class DisponibilidadeService:
    """
    Service for managing psychologist availability schedules.
    
    This service implements the hybrid template + override architecture where:
    - Templates define recurring weekly schedules
    - Overrides provide week-specific adjustments
    - Configs determine how each week behaves
    """
    
    @staticmethod
    def obter_semana_inicio(data):
        """
        Retorna a segunda-feira da semana contendo a data fornecida.
        
        Args:
            data: datetime.date ou datetime.datetime
            
        Returns:
            datetime.date: Segunda-feira da semana (weekday=0)
        """
        if isinstance(data, datetime):
            data = data.date()
        
        return data - timedelta(days=data.weekday())
    
    @staticmethod
    def obter_intervalos_para_semana(psicologo, data_na_semana):
        """
        Retorna os intervalos de disponibilidade para uma semana específica.
        Combina template + overrides conforme a configuração da semana.
        
        Args:
            psicologo: Instância de Psicologo
            data_na_semana: Data contida na semana desejada
            
        Returns:
            list: Lista de objetos de intervalo (podem ser templates convertidos ou overrides)
        """
        semana_inicio = DisponibilidadeService.obter_semana_inicio(data_na_semana)
        
        # Check week configuration
        config = SemanaDisponibilidadeConfig.objects.filter(
            psicologo=psicologo,
            semana_inicio=semana_inicio
        ).first()
        
        if config and config.comportamento == 'UNAVAILABLE':
            return []
        
        if config and config.comportamento == 'CUSTOM':
            # Use only overrides, ignore template
            overrides = IntervaloDisponibilidadeOverride.objects.filter(
                psicologo=psicologo,
                semana_inicio=semana_inicio
            )
            return list(overrides)
        
        # Default: use template + overrides
        intervalos = []
        
        # Convert template to real dates for this week
        templates = psicologo.disponibilidade_template.all()
        for template in templates:
            intervalo_real = DisponibilidadeService._converter_template_para_data(
                template, semana_inicio
            )
            intervalos.append(intervalo_real)
        
        # Add any overrides (additional slots)
        overrides = IntervaloDisponibilidadeOverride.objects.filter(
            psicologo=psicologo,
            semana_inicio=semana_inicio
        )
        intervalos.extend(overrides)
        
        return intervalos
    
    @staticmethod
    def _converter_template_para_data(template, semana_inicio):
        """
        Converte um template para um intervalo com datas reais.
        
        Args:
            template: IntervaloDisponibilidadeTemplate
            semana_inicio: datetime.date (Monday)
            
        Returns:
            dict: Dicionário com data_hora_inicio, data_hora_fim, is_template
        """
        # Calculate actual dates based on template's weekdays
        days_inicio = template.dia_semana_inicio_iso - 1
        days_fim = template.dia_semana_fim_iso - 1
        
        # Handle wrap around (e.g. Sun 22:00 to Mon 02:00)
        if days_fim < days_inicio or (days_fim == days_inicio and template.hora_fim <= template.hora_inicio):
            days_fim += 7
            
        inicio = semana_inicio + timedelta(days=days_inicio)
        fim = semana_inicio + timedelta(days=days_fim)
        
        # Use UTC as reference timezone for templates to ensure consistency
        # This assumes templates are stored in UTC or a fixed server time
        from datetime import UTC
        fuso_referencia = UTC
        
        data_hora_inicio = timezone.make_aware(
            datetime.combine(inicio, template.hora_inicio),
            fuso_referencia
        )
        data_hora_fim = timezone.make_aware(
            datetime.combine(fim, template.hora_fim),
            fuso_referencia
        )
        
        # Return a dict for compatibility (can be converted to NamedTuple later if needed)
        return {
            'data_hora_inicio': data_hora_inicio,
            'data_hora_fim': data_hora_fim,
            'is_template': True,
            'template': template,
        }
    
    @staticmethod
    def tem_disponibilidade_na_semana(psicologo, data_na_semana):
        """
        Verifica se há disponibilidade definida para a semana.
        
        Args:
            psicologo: Instância de Psicologo
            data_na_semana: Data contida na semana a verificar
            
        Returns:
            bool: True se há disponibilidade, False caso contrário
        """
        # Must have either template or overrides for this week
        tem_template = psicologo.disponibilidade_template.exists()
        
        if tem_template:
            semana_inicio = DisponibilidadeService.obter_semana_inicio(data_na_semana)
            
            # Check if week is explicitly marked as unavailable
            config = SemanaDisponibilidadeConfig.objects.filter(
                psicologo=psicologo,
                semana_inicio=semana_inicio,
                comportamento='UNAVAILABLE'
            ).exists()
            
            return not config
        
        # Check if has overrides for this week (CUSTOM mode without template)
        semana_inicio = DisponibilidadeService.obter_semana_inicio(data_na_semana)
        tem_overrides = IntervaloDisponibilidadeOverride.objects.filter(
            psicologo=psicologo,
            semana_inicio=semana_inicio
        ).exists()
        
        return tem_overrides
    
    @staticmethod
    def replicar_template_para_semanas(psicologo, semana_inicio, num_semanas):
        """
        Cria configurações de semanas para usar o template.
        Apenas marca as semanas como 'TEMPLATE', não cria overrides.
        
        Args:
            psicologo: Instância de Psicologo
            semana_inicio: Data de início da primeira semana (Monday)
            num_semanas: Número de semanas futuras (0-52)
            
        Returns:
            list: Lista de SemanaDisponibilidadeConfig criadas
        """
        configs_criadas = []
        
        for i in range(1, num_semanas + 1):
            data_semana = semana_inicio + timedelta(weeks=i)
            config, created = SemanaDisponibilidadeConfig.objects.get_or_create(
                psicologo=psicologo,
                semana_inicio=data_semana,
                defaults={'comportamento': 'TEMPLATE'}
            )
            if created:
                configs_criadas.append(config)
        
        return configs_criadas
    
    @staticmethod
    def salvar_template_de_matriz(psicologo, matriz_disponibilidade):
        """
        Converte a matriz de disponibilidade em templates e salva.
        Remove templates antigos e cria novos.
        
        Args:
            psicologo: Instância de Psicologo
            matriz_disponibilidade: Matriz JSON de disponibilidade (7x48 ou 7xN)
            
        Returns:
            list: Lista de IntervaloDisponibilidadeTemplate criados
        """
        # Convert matrix to intervals (reuse existing logic)
        intervalos = IntervaloDisponibilidade.from_matriz(matriz_disponibilidade)
        
        # Delete old templates
        psicologo.disponibilidade_template.all().delete()
        
        # Create new templates
        templates = []
        for intervalo in intervalos:
            template = IntervaloDisponibilidadeTemplate(
                psicologo=psicologo,
                dia_semana_inicio_iso=intervalo.dia_semana_inicio_local,
                hora_inicio=intervalo.hora_inicio_local,
                dia_semana_fim_iso=intervalo.dia_semana_fim_local,
                hora_fim=intervalo.hora_fim_local,
            )
            templates.append(template)
        
        IntervaloDisponibilidadeTemplate.objects.bulk_create(templates)
        return templates

    @staticmethod
    def salvar_override_semana(psicologo, semana_referencia, matriz_disponibilidade):
        """
        Salva uma configuração específica (Override) para uma semana.
        
        Args:
            psicologo: Instância de Psicologo
            semana_referencia: Data de início da semana (Monday)
            matriz_disponibilidade: Matriz JSON de disponibilidade
        """
        semana_inicio = DisponibilidadeService.obter_semana_inicio(semana_referencia)
        
        # 1. Set week config to CUSTOM
        SemanaDisponibilidadeConfig.objects.update_or_create(
            psicologo=psicologo,
            semana_inicio=semana_inicio,
            defaults={'comportamento': 'CUSTOM'}
        )
        
        # 2. Clear existing overrides for this week
        IntervaloDisponibilidadeOverride.objects.filter(
            psicologo=psicologo,
            semana_inicio=semana_inicio
        ).delete()
        
        # 3. Create new overrides from matrix
        intervalos = IntervaloDisponibilidade.from_matriz(matriz_disponibilidade)
        overrides = []
        
        # Use UTC as reference timezone for overrides to ensure consistency
        from datetime import UTC
        fuso_referencia = UTC
        
        for intervalo in intervalos:
            # Calculate actual dates based on week start + weekday offset
            days_inicio = intervalo.dia_semana_inicio_local - 1
            days_fim = intervalo.dia_semana_fim_local - 1
            
            # Handle wrap around
            if days_fim < days_inicio or (days_fim == days_inicio and intervalo.hora_fim_local <= intervalo.hora_inicio_local):
                days_fim += 7
                
            inicio = semana_inicio + timedelta(days=days_inicio)
            fim = semana_inicio + timedelta(days=days_fim)
            
            data_hora_inicio = timezone.make_aware(
                datetime.combine(inicio, intervalo.hora_inicio_local),
                fuso_referencia
            )
            data_hora_fim = timezone.make_aware(
                datetime.combine(fim, intervalo.hora_fim_local),
                fuso_referencia
            )
            
            override = IntervaloDisponibilidadeOverride(
                psicologo=psicologo,
                semana_inicio=semana_inicio,
                data_hora_inicio=data_hora_inicio,
                data_hora_fim=data_hora_fim
            )
            overrides.append(override)
            
        IntervaloDisponibilidadeOverride.objects.bulk_create(overrides)

    @staticmethod
    def definir_novo_padrao_a_partir_de(psicologo, semana_referencia, matriz_disponibilidade):
        """
        Define um novo padrão (Template) a partir de uma semana específica.
        Preserva o histórico de semanas anteriores criando Overrides se necessário.
        Limpa Overrides de semanas futuras para que sigam o novo padrão.
        
        Args:
            psicologo: Instância de Psicologo
            semana_referencia: Data de início da semana que define o novo padrão
            matriz_disponibilidade: Matriz JSON com a nova configuração
        """
        semana_inicio_ref = DisponibilidadeService.obter_semana_inicio(semana_referencia)
        
        # 1. Freeze history: For weeks < semana_referencia that use TEMPLATE, create explicit Overrides
        # We only care about weeks that have actual appointments or are in the recent past/future window
        # For simplicity, let's look at weeks with existing Configs or just assume a window if needed.
        # However, a safer approach is: if we change the template, ALL past weeks that relied on it change.
        # So we MUST create overrides for them.
        # Strategy: Iterate backwards from semana_ref until we find a week with explicit config or hit a limit?
        # Better: Just check weeks that have appointments? No, availability is separate.
        # Let's assume we want to preserve history for the last 52 weeks or since the user started.
        
        # Actually, we can just check if there are any weeks BEFORE this one that DO NOT have a CUSTOM config.
        # But iterating all past weeks is expensive.
        # Let's compromise: Freeze history for weeks that have Config=TEMPLATE or None (implicit template).
        # But we need to know what the OLD template was to freeze it.
        
        # Step 1.1: Get current template intervals (before we delete them)
        old_templates = list(psicologo.disponibilidade_template.all())
        
        # If no old template existed, nothing to freeze (past was empty/unavailable unless overridden)
        if old_templates:
            # Find weeks before reference that need freezing
            # We can't easily find "all weeks ever", so let's focus on weeks that have explicit Config='TEMPLATE'
            # or weeks that have Appointments?
            # User requirement: "não deve alterar... horários previamente definidos da semana1, semana2..."
            # This implies we should freeze weeks that the user has "touched" or "lived through".
            
            # Let's freeze weeks from "today" backwards to some limit, or all weeks with 'TEMPLATE' config.
            # A simple heuristic: Freeze weeks that have a 'TEMPLATE' config object.
            configs_to_freeze = SemanaDisponibilidadeConfig.objects.filter(
                psicologo=psicologo,
                semana_inicio__lt=semana_inicio_ref,
                comportamento='TEMPLATE'
            )
            
            for config in configs_to_freeze:
                # Convert old template to override for this week
                overrides = []
                from datetime import UTC
                fuso_referencia = UTC
                
                for template in old_templates:
                    # Logic similar to _converter_template_para_data but creating Override objects
                    days_inicio = template.dia_semana_inicio_iso - 1
                    days_fim = template.dia_semana_fim_iso - 1
                    
                    if days_fim < days_inicio or (days_fim == days_inicio and template.hora_fim <= template.hora_inicio):
                        days_fim += 7
                        
                    inicio = config.semana_inicio + timedelta(days=days_inicio)
                    fim = config.semana_inicio + timedelta(days=days_fim)
                    
                    data_hora_inicio = timezone.make_aware(
                        datetime.combine(inicio, template.hora_inicio),
                        fuso_referencia
                    )
                    data_hora_fim = timezone.make_aware(
                        datetime.combine(fim, template.hora_fim),
                        fuso_referencia
                    )
                    
                    overrides.append(IntervaloDisponibilidadeOverride(
                        psicologo=psicologo,
                        semana_inicio=config.semana_inicio,
                        data_hora_inicio=data_hora_inicio,
                        data_hora_fim=data_hora_fim
                    ))
                
                IntervaloDisponibilidadeOverride.objects.bulk_create(overrides)
                
                # Update config to CUSTOM
                config.comportamento = 'CUSTOM'
                config.save()

        # 2. Update Global Template
        DisponibilidadeService.salvar_template_de_matriz(psicologo, matriz_disponibilidade)
        
        # 3. Clear Future Overrides (weeks >= semana_referencia)
        # This ensures they inherit the new template
        SemanaDisponibilidadeConfig.objects.filter(
            psicologo=psicologo,
            semana_inicio__gte=semana_inicio_ref
        ).delete()
        
        IntervaloDisponibilidadeOverride.objects.filter(
            psicologo=psicologo,
            semana_inicio__gte=semana_inicio_ref
        ).delete()
        
        # Ensure the reference week itself is set to use TEMPLATE (implicit by deletion above, but let's be explicit if needed)
        # Actually, deleting the config makes it fall back to default behavior (Template).
        # But if we want to be explicit:
        SemanaDisponibilidadeConfig.objects.create(
            psicologo=psicologo,
            semana_inicio=semana_inicio_ref,
            comportamento='TEMPLATE'
        )
