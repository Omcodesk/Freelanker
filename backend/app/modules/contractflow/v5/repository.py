"""Atomic single-process storage; replace with transactional PostgreSQL in V6."""

from threading import RLock
from typing import Callable, Protocol
from uuid import UUID

from .audit import event
from .errors import NotFound, PersistenceError, StaleVersion
from .schemas import ApprovalRecord, ApprovalSubject, TrustedActor
from .validation import validate_record


class ApprovalRepository(Protocol):
    async def load(self, amendment_id: UUID) -> ApprovalRecord: ...

    async def history(self, amendment_id: UUID) -> tuple: ...

    async def publish(self, subject: ApprovalSubject, actor: TrustedActor) -> ApprovalRecord: ...

    async def transact(self, amendment_id: UUID, operation: Callable[[ApprovalRecord], ApprovalRecord]) -> ApprovalRecord:
        """Run callback on current state with serializable isolation; commit audit and state together.

        V6 adapters may use CAS and retry internally, never re-run external effects.
        Callback is synchronous, deterministic except server IDs/time, and performs no I/O.
        """
        ...


class InMemoryApprovalRepository:
    """Thread/asyncio safe within one process; no durability or distributed safety.

    No await occurs under the RLock. Immutable values are detached on load/write;
    a single dictionary replacement is the commit point for audit and state.
    """

    def __init__(self):
        self._lock = RLock()
        self._records = {}

    def _commit(self, replacement):
        # Fault-injection seam: raise BEFORE replacement to simulate audit/storage
        # failure. An external audit write cannot be split from this transaction.
        self._records = replacement

    def _current(self, amendment_id):
        versions = [version for key, version in self._records if key == amendment_id]
        if not versions:
            raise NotFound("Unknown amendment")
        return validate_record(self._records[(amendment_id, max(versions))])

    async def load(self, amendment_id):
        with self._lock:
            return self._current(amendment_id)

    async def history(self, amendment_id):
        with self._lock:
            self._current(amendment_id)
            records = [validate_record(record) for (key, version), record in sorted(
                self._records.items(), key=lambda item: item[0][1]) if key == amendment_id]
            return tuple(event for record in records for event in record.events)

    async def publish(self, subject, actor):
        with self._lock:
            replacement = dict(self._records)
            existing = any(key == subject.amendment_id for key, version in replacement)
            if existing:
                old = self._current(subject.amendment_id)
                a, b = old.subject.draft, subject.draft
                if (subject.amendment_version != old.subject.amendment_version + 1
                        or a.original_facts != b.original_facts
                        or (a.original_agreement_id, a.original_agreement_version, a.project_id) !=
                           (b.original_agreement_id, b.original_agreement_version, b.project_id)
                        or a.model_dump(mode="json") == b.model_dump(mode="json")):
                    raise StaleVersion("Revision requires changed content and the next version of the same agreement")
                superseded = event(old.subject, actor, "SUPERSEDED", old.state, "SUPERSEDED")
                old = ApprovalRecord(subject=old.subject, state="SUPERSEDED", decisions=old.decisions,
                                     events=old.events + (superseded,))
                replacement[(subject.amendment_id, old.subject.amendment_version)] = validate_record(old)
            elif subject.amendment_version != 1:
                raise StaleVersion("First amendment version must be one")
            created = event(subject, actor, "CREATED", None, "PENDING_REVIEW")
            result = validate_record(ApprovalRecord(subject=subject, events=(created,)))
            replacement[(subject.amendment_id, subject.amendment_version)] = result
            self._write(replacement)
            return result

    def _write(self, replacement):
        previous = self._records
        try:
            self._commit(replacement)
        except Exception:
            self._records = previous
            raise PersistenceError("Approval and audit transaction failed") from None

    async def transact(self, amendment_id, operation):
        with self._lock:
            current = self._current(amendment_id)
            result = validate_record(operation(current))
            if result.subject != current.subject or result.events[:len(current.events)] != current.events:
                raise PersistenceError("Transaction cannot replace subject or audit history")
            replacement = dict(self._records)
            replacement[(amendment_id, current.subject.amendment_version)] = result
            self._write(replacement)
            return result
