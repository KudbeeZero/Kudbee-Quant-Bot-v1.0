"""Secrets handling — scaffolding for future live trading / broker keys.

Principles (enforced here so they're true before we ever go live):
  - Secrets come from environment variables only — never hardcoded, never
    committed, never written to the cache or any data file.
  - A SecretStr never reveals its value in ``repr``/``str``/logs/tracebacks;
    you must call ``.reveal()`` explicitly at the point of use.
  - Missing required secrets fail loudly rather than defaulting to something.

No secret values live in this module; it only reads ``os.environ`` on demand.
"""
from __future__ import annotations

import os


class SecretStr:
    """A string whose value is hidden from logs and reprs.

    Call ``.reveal()`` only at the moment you must pass it to a client. The
    masked forms make it safe to log objects/configs that contain secrets.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str):
        if not isinstance(value, str):
            raise TypeError("SecretStr requires a str")
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __repr__(self) -> str:
        return "SecretStr('***')"

    __str__ = __repr__

    def __eq__(self, other: object) -> bool:  # constant-ish; avoid leaking via ==
        return isinstance(other, SecretStr) and other._value == self._value

    def __hash__(self) -> int:
        return hash(("SecretStr", self._value))


def get_secret(name: str, *, required: bool = True, default: str | None = None) -> SecretStr | None:
    """Read a secret from the environment, wrapped so it can't leak in logs.

    Args:
        name: environment variable name (e.g. "POLYMARKET_API_KEY").
        required: if True and unset, raise; if False, return ``default``.
    """
    value = os.environ.get(name)
    if value is None or value == "":
        if required:
            raise RuntimeError(
                f"required secret {name!r} is not set; export it in the environment "
                "(never hardcode or commit secrets)"
            )
        return SecretStr(default) if default is not None else None
    return SecretStr(value)
