"""Output port for asynchronous transactional-outbox delivery operations."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.application.enums.outbox_failures import OutboxFailureCategory
from src.application.eventing.outbox.message import OutboxMessage


class OutboxRepositoryPort(Protocol):
    """Claim, acknowledge, retry, and remove persisted outbox messages.

    Implementations own a short database transaction for each method. Claiming
    must be atomic across concurrent workers, normally through row locking with
    skip-locked semantics. A worker may mutate a claimed row only while both
    its ``outbox_id`` and opaque ``claim_token`` still match the persisted
    lease.

    This worker-facing port intentionally excludes insertion. New drafts are
    written through ``UnitOfWorkOutboxRepositoryPort`` so business changes and
    their outbox rows commit atomically.
    """

    def claim_batch(
        self,
        *,
        now: datetime,
        claimed_until: datetime,
        limit: int,
        claim_token: UUID,
    ) -> tuple[OutboxMessage, ...]:
        """Atomically claim a bounded batch of currently eligible messages.

        Eligible rows are unpublished, available at or before ``now``, and
        either unclaimed or protected by an expired lease. Implementations
        assign the supplied token and expiry, increment each row's attempt
        count, and return a fully materialized ordered tuple. Expired claims
        may be reclaimed directly without a preceding release operation.

        Args:
            now: Current UTC timestamp used for availability and lease checks.
            claimed_until: UTC lease expiry, strictly later than ``now``.
            limit: Positive maximum number of rows to claim.
            claim_token: Opaque token identifying this worker's batch claim.

        Returns:
            Claimed messages ordered by availability and stable row identity.
            Every returned message carries ``claim_token`` and
            ``claimed_until``.
        """
        ...

    def mark_published(self, *, outbox_id: int, claim_token: UUID, published_at: datetime) -> bool:
        """Complete one message while the caller still owns its lease.

        Successful completion assigns ``published_at`` and clears claim and
        failure metadata. The update must require a matching claim token and a
        lease that has not expired at ``published_at``.

        Args:
            outbox_id: Positive identity of the claimed outbox row.
            claim_token: Token returned by the successful claim operation.
            published_at: UTC time at which publication completed.

        Returns:
            ``True`` when the row was completed; ``False`` when the row was no
            longer owned, its lease had expired, or it was already published.
        """
        ...

    def mark_failed(
        self,
        *,
        outbox_id: int,
        claim_token: UUID,
        failed_at: datetime,
        failure_category: OutboxFailureCategory,
        last_error: str,
        available_at: datetime,
    ) -> bool:
        """Record a failed attempt and schedule the message for retry.

        Successful failure handling clears the active claim, stores the
        machine-readable category and diagnostic text, and moves
        ``available_at`` to the next retry time. The update must require a
        matching token and a lease valid at ``failed_at``.

        Args:
            outbox_id: Positive identity of the claimed outbox row.
            claim_token: Token returned by the successful claim operation.
            failed_at: UTC time at which the attempt failed.
            failure_category: Stable classification of the processing failure.
            last_error: Non-empty operational diagnostic for the failure.
            available_at: UTC timestamp at or after ``failed_at`` when the
                message becomes eligible for another attempt.

        Returns:
            ``True`` when failure state was recorded; ``False`` when ownership
            was lost, the lease had expired, or the row was already published.
        """
        ...

    def release_expired_claims(self, *, now: datetime, limit: int) -> int:
        """Clear a bounded number of expired unpublished claims.

        Normal claiming may reclaim expired leases directly. This method is
        intended for explicit maintenance and operational visibility.

        Args:
            now: Current UTC timestamp used to identify expired leases.
            limit: Positive maximum number of claims to release.

        Returns:
            Number of rows whose claim token and expiry were cleared.
        """
        ...

    def delete_published_before(self, *, cutoff: datetime, limit: int) -> int:
        """Delete a bounded batch of successfully published historical rows.

        Args:
            cutoff: UTC timestamp; only rows published strictly before it may
                be deleted.
            limit: Positive maximum number of rows to delete.

        Returns:
            Number of published rows deleted. Unpublished and failed rows are
            never eligible for this operation.
        """
        ...
