from zoneinfo import ZoneInfo
from datetime import UTC
from django.utils import timezone

FUSOS_PARA_TESTE = [
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