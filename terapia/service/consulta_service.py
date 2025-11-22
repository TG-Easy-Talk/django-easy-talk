"""
Consulta Service - Business logic for appointment operations.

This service centralizes logic for creating and managing appointments,
removing it from views.
"""
from typing import Tuple, List
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from terapia.models import Consulta


class ConsultaService:
    """
    Service para operações de consulta.
    Separa business logic das views (Single Responsibility Principle).
    """
    
    @staticmethod
    def criar_multiplas_consultas(
        paciente,
        psicologo,
        slots: List[str],
        timezone_obj
    ) -> Tuple[int, List[Tuple[str, str]]]:
        """
        Cria múltiplas consultas de uma vez, validando cada uma.
        
        Esta lógica foi movida de PerfilView.post para melhorar testabilidade
        e reutilização (ex: poderia ser usada em uma API REST).
        
        Args:
            paciente: Instância de Paciente
            psicologo: Instância de Psicologo
            slots: Lista de strings ISO datetime para agendar
            timezone_obj: Timezone object para converter datas
            
        Returns:
            Tupla (criadas, falhas) onde:
                - criadas: int com quantidade de consultas criadas
                - falhas: Lista de tuplas (slot, mensagem_erro)
        """
        criadas = 0
        falhas = []
        
        with transaction.atomic():
            for slot in slots:
                try:
                    dt_naive = datetime.fromisoformat(slot)
                    dt = timezone.make_aware(dt_naive, timezone_obj)
                    
                    consulta = Consulta(
                        paciente=paciente,
                        psicologo=psicologo,
                        data_hora_agendada=dt
                    )
                    consulta.full_clean()
                    consulta.save()
                    criadas += 1
                    
                except ValidationError as ve:
                    # Concatenar todas as mensagens de erro
                    mensagens_erro = "; ".join(sum(ve.message_dict.values(), []))
                    falhas.append((slot, mensagens_erro))
                    
                except Exception as e:
                    falhas.append((slot, str(e)))
        
        return criadas, falhas
    
    @staticmethod
    def atualizar_estado_consulta(consulta, novo_estado, usuario_atualizacao=None):
        """
        Atualiza o estado de uma consulta com validações apropriadas.
        
        Args:
            consulta: Instância de Consulta
            novo_estado: Novo estado (valor de EstadoConsulta)
            usuario_atualizacao: Usuário que está fazendo a atualização (opcional)
            
        Returns:
            bool: True se atualizou, False se já estava nesse estado
            
        Raises:
            ValidationError: Se transição de estado não é permitida
        """
        from terapia.models import EstadoConsulta
        
        if consulta.estado == novo_estado:
            return False
        
        # Validar transições permitidas
        transicoes_proibidas = {
            EstadoConsulta.CANCELADA: [EstadoConsulta.CONFIRMADA, EstadoConsulta.EM_ANDAMENTO],
            EstadoConsulta.FINALIZADA: [
                EstadoConsulta.SOLICITADA,
                EstadoConsulta.CONFIRMADA,
                EstadoConsulta.CANCELADA,
            ],
        }
        
        if consulta.estado in transicoes_proibidas:
            if novo_estado in transicoes_proibidas[consulta.estado]:
                raise ValidationError(
                    f"Não é possível mudar de {consulta.get_estado_display()} "
                    f"para {EstadoConsulta(novo_estado).label}"
                )
        
        consulta.estado = novo_estado
        consulta.save(update_fields=['estado'])
        return True
