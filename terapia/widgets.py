from django import forms


class CustomDateInput(forms.DateInput):
    input_type = 'date'


class CustomDateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


class DisponibilidadeInput(forms.HiddenInput):
    template_name = 'meu_perfil/componentes/disponibilidade_widget.html'

    def __init__(self, disponibilidade=None, attrs=None):
        super().__init__(attrs)
        self.disponibilidade = disponibilidade

    def format_value(self, value):
        matriz = [[False] * 24 for _ in range(7)]

        if self.disponibilidade.exists():
            for intervalo in self.disponibilidade.all():
                dia = intervalo.data_hora_inicio.isoweekday() % 7 # Ajusta para 0 = Domingo, 6 = Sábado
                hora_inicio = intervalo.data_hora_inicio.hour
                hora_fim = intervalo.data_hora_fim.hour
                for hora in range(hora_inicio, hora_fim):
                    matriz[dia][hora] = True

        print(matriz)
        return matriz