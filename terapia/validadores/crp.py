import re
from django.core.exceptions import ValidationError

# 1) 16/331 -> RR / 3 dígitos
# 2) 16/5154  -> RR / 4 dígitos
# 3) 01/17866 -> RR / 5 dígitos
# 4) 06/166340 -> RR / 6 dígitos
# 5) 03/0010327 -> RR / 7 dígitos (permite zeros à esquerda)
# 6) 14/05473-7 -> RR / 5 dígitos + hífen + DV (1 dígito)
# 7) 02/IS265 -> RR / 2 letras + 3 dígitos
# 8) 03/IS01083 -> RR / 2 letras + 5 dígitos
# 9) 04/IP003974 -> RR / 2 letras + 6 dígitos

_CRP_NUM3_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<seq>\d{3})$", re.IGNORECASE)
_CRP_NUM4_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<seq>\d{4})$", re.IGNORECASE)
_CRP_NUM5_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<seq>\d{5})$", re.IGNORECASE)
_CRP_NUM6_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<seq>\d{6})$", re.IGNORECASE)
_CRP_NUM7_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<seq>\d{7})$", re.IGNORECASE)
_CRP_NUM5_DV_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<seq>\d{5})-(?P<dv>\d)$", re.IGNORECASE)
_CRP_ALPHA3_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<letras>[A-Z]{2})(?P<seq>\d{3})$", re.IGNORECASE)
_CRP_ALPHA5_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<letras>[A-Z]{2})(?P<seq>\d{5})$", re.IGNORECASE)
_CRP_ALPHA6_RE = re.compile(r"^(?:CRP\s*)?(?P<rr>\d{2})/(?P<letras>[A-Z]{2})(?P<seq>\d{6})$", re.IGNORECASE)

_CRP_PATTERNS = [
    _CRP_NUM3_RE,
    _CRP_NUM4_RE,
    _CRP_NUM5_RE,
    _CRP_NUM6_RE,
    _CRP_NUM7_RE,
    _CRP_NUM5_DV_RE,
    _CRP_ALPHA3_RE,
    _CRP_ALPHA5_RE,
    _CRP_ALPHA6_RE,
]


def validar_crp(crp: str) -> bool:
    s = crp or ""
    for rx in _CRP_PATTERNS:
        m = rx.fullmatch(s)
        if not m:
            continue
        rr = int(m.group("rr"))
        if not (1 <= rr <= 24):
            return False
        seq = m.group("seq")
        return any(ch != "0" for ch in seq)
    return False


def validate_crp(value: str) -> None:
    if not validar_crp(value):
        raise ValidationError(
            "Este CRP é inválido ou não foi formatado corretamente.",
            code="crp_invalido",
        )
