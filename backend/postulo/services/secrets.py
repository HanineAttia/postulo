"""Secrets (API keys) in the system credential manager, via keyring (SPEC 2.3).

Secrets are never written to settings.json, never logged and never sent back to
the frontend. Fallback: the ANTHROPIC_API_KEY environment variable (read-only).
TODO: encrypted local fallback (SPEC 2.3) for systems without a usable keyring.
"""

from __future__ import annotations

import contextlib
import os
from enum import StrEnum

import keyring
from keyring.errors import KeyringError

from postulo import APP_NAME


class Secret(StrEnum):
    ANTHROPIC_API_KEY = "anthropic_api_key"


_ENV_FALLBACK = {Secret.ANTHROPIC_API_KEY: "ANTHROPIC_API_KEY"}


class SecretStoreError(Exception):
    """The credential manager is unavailable (French, user-facing message)."""


def get_secret(name: Secret) -> str | None:
    try:
        value = keyring.get_password(APP_NAME, name.value)
    except KeyringError:
        value = None
    if value:
        return value
    env_name = _ENV_FALLBACK.get(name)
    return os.environ.get(env_name) or None if env_name else None


def set_secret(name: Secret, value: str) -> None:
    try:
        keyring.set_password(APP_NAME, name.value, value)
    except KeyringError as exc:
        raise SecretStoreError(
            "Le gestionnaire d'identifiants du système est indisponible : la clé n'a pas pu "
            "être enregistrée. Tu peux définir la variable d'environnement ANTHROPIC_API_KEY."
        ) from exc


def delete_secret(name: Secret) -> None:
    with contextlib.suppress(KeyringError):  # already absent, or no backend
        keyring.delete_password(APP_NAME, name.value)


def has_secret(name: Secret) -> bool:
    return get_secret(name) is not None
