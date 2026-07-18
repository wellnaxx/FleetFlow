from src.adapters.driven.persistence.database.executor import RowDict, fetch_one
from src.adapters.driven.persistence.database.queries import QUERIES
from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.shared.validation import require_int


def load_snapshot_counters() -> CountersSnapshot:
    row = fetch_one(QUERIES.world_state.get_snapshot_counters)
    if row is None:
        raise ValueError("Snapshot counter query returned no row.")

    return CountersSnapshot(
        next_customer_id=_required_int(row, "next_customer_id"),
        next_package_id=_required_int(row, "next_package_id"),
        next_route_id=_required_int(row, "next_route_id"),
    )


def _required_int(row: RowDict, column: str) -> int:
    return require_int(row[column], column)
