"""World state snapshot schema versioning constants.

These are code-level constants, not operator configuration.
They change only when the snapshot format changes and the
preparer is updated to handle the new version.
"""

SCHEMA_VERSION: int = 2
SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1, 2})

if SCHEMA_VERSION not in SUPPORTED_SCHEMA_VERSIONS:
    raise ValueError(
        f"SCHEMA_VERSION {SCHEMA_VERSION} must be included in "
        f"SUPPORTED_SCHEMA_VERSIONS {sorted(SUPPORTED_SCHEMA_VERSIONS)}."
    )
