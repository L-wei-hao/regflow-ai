from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Action(str, Enum):
    MANAGE_WORKFLOWS = "manage_workflows"
    CREATE_CASES = "create_cases"
    READ_CASES = "read_cases"
    REVIEW_CASES = "review_cases"
    RESOLVE_CASES = "resolve_cases"
    READ_AUDIT_TRAIL = "read_audit_trail"


@dataclass(frozen=True, slots=True)
class UserPrincipal:
    user_id: str
    display_name: str
    role: UserRole


class AccessControl:
    _role_permissions: dict[UserRole, set[Action]] = {
        UserRole.ADMIN: {
            Action.MANAGE_WORKFLOWS,
            Action.CREATE_CASES,
            Action.READ_CASES,
            Action.REVIEW_CASES,
            Action.RESOLVE_CASES,
            Action.READ_AUDIT_TRAIL,
        },
        UserRole.ANALYST: {
            Action.CREATE_CASES,
            Action.READ_CASES,
            Action.REVIEW_CASES,
        },
        UserRole.REVIEWER: {
            Action.READ_CASES,
            Action.REVIEW_CASES,
            Action.RESOLVE_CASES,
        },
        UserRole.VIEWER: {
            Action.READ_CASES,
        },
    }

    def can(self, principal: UserPrincipal, action: Action) -> bool:
        return action in self._role_permissions.get(principal.role, set())

    def require(self, principal: UserPrincipal, action: Action) -> None:
        if not self.can(principal, action):
            raise PermissionError(f"{principal.role.value} cannot {action.value}")
