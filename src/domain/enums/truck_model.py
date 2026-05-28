"""Supported truck model names."""

from __future__ import annotations

from enum import StrEnum

from src.domain.exceptions import DomainValidationError


class TruckModel(StrEnum):
    """Truck models available in the fixed fleet."""

    SCANIA = "Scania"
    MAN = "Man"
    ACTROS = "Actros"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return persisted/display values for all supported truck models."""
        return tuple(model.value for model in cls)

    @classmethod
    def labels(cls) -> str:
        """Return a readable model list for validation messages."""
        values = cls.values()
        return f"{', '.join(values[:-1])} or {values[-1]}"

    @classmethod
    def from_value(cls, value: str | TruckModel) -> TruckModel:
        """Normalize a raw model name to a supported truck model.

        Args:
            value: Raw persisted/display model value or existing enum member.

        Returns:
            Supported truck model enum member.

        Raises:
            DomainValidationError: If the model value is unsupported.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError as exc:
            raise DomainValidationError(f"Truck name must be {cls.labels()}") from exc
