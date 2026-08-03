"""Typed messages and routing keys for state-changing application requests."""

from dataclasses import dataclass


class Command:
    """Marker base for an application request that may change state.

    Commands carry validated application input but do not contain adapter
    concerns such as CLI tokens, HTTP request models, dependency resolution,
    or handler execution. Concrete commands should normally be immutable
    dataclasses so one dispatch observes a stable request value.
    """

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class CommandKey[C: Command, R]:
    """Bind one concrete command type to its handler result type.

    ``R`` is a phantom static type parameter: it intentionally has no runtime
    field. An explicit annotation on each key declaration supplies that result
    type to the type checker and lets ``CommandBus.dispatch`` infer its return
    type. The concrete bus uses ``name`` and ``command_type`` for registration
    and runtime routing.

    Attributes:
        name: Stable, application-wide routing name for the command.
        command_type: Exact concrete command class accepted by the binding.
    """

    name: str
    command_type: type[C]
