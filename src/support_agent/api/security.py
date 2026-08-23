"""Hashed API-key role boundary for the local PoC."""

import hashlib
import secrets
from dataclasses import dataclass
from enum import StrEnum

from fastapi import HTTPException, Request, status


class Role(StrEnum):
    REVIEWER = "reviewer"
    EXECUTOR = "executor"
    AUDITOR = "auditor"


@dataclass(frozen=True, slots=True)
class Principal:
    actor: str
    role: Role


def authorize(request: Request, allowed_roles: frozenset[Role]) -> Principal:
    """Resolve a configured API key and enforce an endpoint role."""

    supplied_key = request.headers.get("X-API-Key", "")
    supplied_hash = hashlib.sha256(supplied_key.encode("utf-8")).hexdigest()
    settings = request.app.state.settings
    candidates = (
        (settings.reviewer_api_key_sha256, Principal(settings.reviewer_actor, Role.REVIEWER)),
        (settings.executor_api_key_sha256, Principal(settings.executor_actor, Role.EXECUTOR)),
        (settings.auditor_api_key_sha256, Principal(settings.auditor_actor, Role.AUDITOR)),
    )
    principal = next(
        (item for key, item in candidates if key and secrets.compare_digest(supplied_hash, key)),
        None,
    )
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")
    if principal.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role not permitted")
    return principal
