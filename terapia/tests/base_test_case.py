from datetime import UTC
from zoneinfo import ZoneInfo
from django.utils import timezone
from django.test import SimpleTestCase


class BaseTestCase(SimpleTestCase):
    """
    Classe base para testes que possui atributos comuns que podem
    ser úteis para a escrita de testes.
    """

    fusos_para_teste = [
        UTC,
        timezone.get_default_timezone(),
        timezone.get_current_timezone(),
        ZoneInfo("Asia/Tokyo"),
        ZoneInfo("America/New_York"),
        ZoneInfo("Africa/Cairo"),
        ZoneInfo("Asia/Shanghai"),
        ZoneInfo("Pacific/Chatham"),
        ZoneInfo("Pacific/Marquesas"),
        ZoneInfo("Iran"),
        ZoneInfo("Australia/Eucla"),
    ] + [ZoneInfo(f"Etc/GMT{offset:+}") for offset in range(-14, 13)]