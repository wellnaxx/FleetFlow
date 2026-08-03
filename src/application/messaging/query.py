"""Typed messages and routing keys for read-only application requests."""

from dataclasses import dataclass


class Query:
    """Marker base for an application request that only reads state.

    Queries describe application-level read intent and remain independent of
    CLI parsing, HTTP schemas, persistence technology, and handler resolution.
    Concrete queries should normally be immutable dataclasses so dispatch uses
    a stable set of selection, filtering, and pagination inputs.
    """

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class QueryKey[Q: Query, R]:
    """Bind one concrete query type to its handler result type.

    ``R`` is a phantom static type parameter and is therefore not represented
    by a dataclass field. Each key declaration must explicitly annotate its
    query and result types so ``QueryBus.dispatch`` can infer the result. The
    concrete bus uses the runtime fields for registration and routing.

    Attributes:
        name: Stable, application-wide routing name for the query.
        query_type: Exact concrete query class accepted by the binding.
    """

    name: str
    query_type: type[Q]
