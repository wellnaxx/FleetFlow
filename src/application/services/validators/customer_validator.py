"""Validation for customer-specific world-state snapshot invariants."""

from src.application.dto.world_state_snapshot_dto import CustomerSnapshot
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import WorldStateCorruptionError


class CustomerSnapshotValidator:
    """Validate customer snapshot fields that require collection-wide checks."""

    def validate_customer_uniqueness(self, customers: tuple[CustomerSnapshot, ...]) -> None:
        """Ensure normalized customer email addresses and phone numbers are unique.

        Args:
            customers: Customer snapshots to validate.

        Raises:
            WorldStateCorruptionError: If duplicate normalized contact values exist.
        """
        seen_emails: dict[str, int] = {}
        seen_phones: dict[str, int] = {}

        for customer in customers:
            email = customer.email.strip().lower() if customer.email else ""
            phone = customer.phone.strip() if customer.phone else ""

            if email:
                if email in seen_emails:
                    raise WorldStateCorruptionError(
                        f"Duplicate customer email in snapshot: {customer.email!r} "
                        f"used by customers {seen_emails[email]} and {customer.customer_id}.",
                        reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                    )
                seen_emails[email] = customer.customer_id

            if phone:
                if phone in seen_phones:
                    raise WorldStateCorruptionError(
                        f"Duplicate customer phone in snapshot: {customer.phone!r} "
                        f"used by customers {seen_phones[phone]} and {customer.customer_id}.",
                        reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                    )
                seen_phones[phone] = customer.customer_id
