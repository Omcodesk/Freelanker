"""Sanitized approval domain failures; never include contract or credential data."""


class ApprovalError(Exception):
    pass


class AuthorizationError(ApprovalError):
    pass


class IntegrityError(ApprovalError):
    pass


class NotFound(ApprovalError):
    pass


class StaleVersion(ApprovalError):
    pass


class InvalidTransition(ApprovalError):
    pass


class IdempotencyConflict(ApprovalError):
    pass


class PersistenceError(ApprovalError):
    pass
