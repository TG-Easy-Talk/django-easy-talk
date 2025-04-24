import re
from typing import Optional, Set
from django.core.exceptions import ValidationError

_NON_DIGITS_RE = re.compile(r"\D")
_INVALID_KNOWN: Set[str] = {
    *(str(i) * 11 for i in range(10)),
    "12345678909", "01234567890",
}


def validar_cpf(value: str) -> bool:
    """Valida CPF (11 dígitos + DV) — retorna True se válido."""
    if not value:
        return False
    digits: str = _NON_DIGITS_RE.sub("", value)
    if len(digits) != 11 or digits in _INVALID_KNOWN:
        return False
    for pos in (9, 10):
        total = sum(int(digits[idx]) * (pos + 1 - idx) for idx in range(pos))
        resto = (total * 10) % 11
        if resto == 10:
            resto = 0
        if resto != int(digits[pos]):
            return False
    return True


def validate_cpf(value: Optional[str]) -> None:
    """Validator Django‐style (raise ValidationError)."""
    if not validar_cpf(value or ""):
        raise ValidationError("Este CPF é inválido")
