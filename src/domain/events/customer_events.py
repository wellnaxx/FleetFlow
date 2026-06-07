"""Domain events describing customer lifecycle transitions."""

from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class CustomerCreated(DomainEvent):
    """Event recorded when a new customer is created."""

    customer_id: int
