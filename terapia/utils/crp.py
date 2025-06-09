import re
from django.core.exceptions import ValidationError

_CRP_RE = re.compile(r"^\d{2}/\d{5}$")


def validar_crp(crp: str) -> bool:
    if not _CRP_RE.fullmatch(crp or ""):
        return False
    prefixo = int(crp.split("/")[0])
    return 1 <= prefixo <= 28  # faixas oficiais de UFs


def validate_crp(value: str) -> None:
    if not validar_crp(value):
        raise ValidationError(
            "Este CRP é inválido ou não foi formatado corretamente.",
            code="crp_invalido",
        )
