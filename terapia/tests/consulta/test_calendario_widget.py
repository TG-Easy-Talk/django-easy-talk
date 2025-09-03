import json
import datetime
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from terapia.models import Paciente, Psicologo, Consulta
from terapia.constants import CONSULTA_DURACAO_MAXIMA

User = get_user_model()


def _load_json(resp):
    try:
        return resp.json()
    except Exception:
        return json.loads(resp.content.decode("utf-8"))


class CalendarWidgetApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u_cliente = User.objects.create_user(email="cw_cliente@example.com", password="senha123")
        cls.u_psico = User.objects.create_user(email="cw_psico@example.com", password="senha123")
        cls.paciente = Paciente.objects.create(usuario=cls.u_cliente, nome="Cliente CW", cpf="11122233344")
        cls.psicologo = Psicologo.objects.create(usuario=cls.u_psico, nome_completo="Psico CW", crp="06/99999")

        tz = timezone.get_current_timezone()

        def aware(y, m, d, H=0, M=0):
            return timezone.make_aware(datetime.datetime(y, m, d, H, M, 0), tz)

        cls.template_weekday = 3
        template_start = aware(2024, 7, cls.template_weekday, 9, 0)
        template_end = aware(2024, 7, cls.template_weekday, 12, 0)
        cls.psicologo.disponibilidade.create(data_hora_inicio=template_start, data_hora_fim=template_end)

        now = timezone.localtime()
        days_ahead = (cls.template_weekday - now.isoweekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        cls.real_day = (now + timedelta(days=days_ahead)).date()

        def build_times(h_ini, h_fim, step: datetime.timedelta):
            t = datetime.time(h_ini, 0)
            cur = datetime.datetime.combine(datetime.date(2024, 7, cls.template_weekday), t)
            times = []
            while cur + step <= datetime.datetime(2024, 7, cls.template_weekday, h_fim, 0):
                times.append(cur.strftime("%H:%M"))
                cur += step
            return times

        cls.expected_times = build_times(9, 12, CONSULTA_DURACAO_MAXIMA)

    def _get_slots_json(self, year: int, month: int):
        url = reverse("api_agenda_slots", args=[self.psicologo.id])
        resp = self.client.get(f"{url}?year={year}&month={month}")
        self.assertEqual(resp.status_code, 200)
        data = _load_json(resp)
        self.assertIsInstance(data, dict)
        return data

    def test_slots_endpoint_retorna_estrutura_por_dia(self):
        """
        O endpoint deve retornar um dict: { 'YYYY-MM-DD': ['HH:MM', ...], ... }.
        """
        data = self._get_slots_json(self.real_day.year, self.real_day.month)
        key = self.real_day.strftime("%Y-%m-%d")
        self.assertIn(key, data)
        self.assertIsInstance(data[key], list)
        for s in data[key]:
            self.assertRegex(s, r"^\d{2}:\d{2}$")

    def test_slots_endpoint_lista_todos_os_horarios_do_dia(self):
        """
        Para um dia com disponibilidade 09–12, o JSON precisa conter TODOS os horários
        possíveis, ex.: ['09:00', '10:00', '11:00'] (N = janela / duração).
        """
        data = self._get_slots_json(self.real_day.year, self.real_day.month)
        key = self.real_day.strftime("%Y-%m-%d")
        slots = data.get(key, [])
        for t in self.expected_times:
            self.assertIn(t, slots)
        self.assertEqual(len(slots), len(self.expected_times))

    def test_slots_endpoint_exclui_horario_ja_ocupado(self):
        """
        Se já existir uma Consulta em um dos horários, ele deve sumir da lista do dia.
        """
        self.assertGreaterEqual(len(self.expected_times), 2)
        hora_ocupada = self.expected_times[1]

        H, M = map(int, hora_ocupada.split(":"))
        dt_real = timezone.make_aware(datetime.datetime.combine(self.real_day, datetime.time(H, M)))

        Consulta.objects.create(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_agendada=dt_real,
            duracao=int(CONSULTA_DURACAO_MAXIMA.total_seconds() // 60),
        )

        data = self._get_slots_json(self.real_day.year, self.real_day.month)
        key = self.real_day.strftime("%Y-%m-%d")
        slots = data.get(key, [])

        self.assertIn(self.expected_times[0], slots)
        self.assertNotIn(hora_ocupada, slots)
        for t in self.expected_times[2:]:
            self.assertIn(t, slots)
