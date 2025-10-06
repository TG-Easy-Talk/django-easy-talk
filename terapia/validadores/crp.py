import re
from django.core.exceptions import ValidationError

_CRP_RE = re.compile(
    r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<seq>\d{1,7})(?:-(?P<dv>\d))?$",
    re.IGNORECASE,
)


def validar_crp(crp: str) -> bool:
    m = _CRP_RE.fullmatch(crp or "")
    if not m:
        return False
    rr = int(m.group("rr"))
    seq = m.group("seq")
    return 1 <= rr <= 24 and any(ch != "0" for ch in seq)


def validate_crp(value: str) -> None:
    if not validar_crp(value):
        raise ValidationError(
            "Este CRP é inválido ou não foi formatado corretamente.",
            code="crp_invalido",
        )
