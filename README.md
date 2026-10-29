# FleetFlow

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/Interface-CLI%20%2B%20HTTP-0F766E)
![Architecture](https://img.shields.io/badge/Architecture-Hexagonal--style-8B5CF6)
![Tests](https://img.shields.io/badge/Tests-pytest%20%2B%20unittest-2563EB)

FleetFlow manages packages, delivery routes, trucks, and customers across Australian freight hubs.
An interactive CLI and FastAPI API share application workflows, with in-memory or PostgreSQL persistence.

## Capabilities

- Package creation, lookup, removal, route assignment, and unassigned-package listing.
- Route scheduling, package/truck assignment, suitability checks, and progress tracking.
- Fixed truck fleet with deterministic city dispersion and segment-based capacity checks.
- Customer records created with packages, with email and phone lookup indexes.
- Fleet overview with status counts, overdue work, active-route positions, and truck utilization.
- Manager/employee authorization, password hashing, and HTTP JWT authentication with token revocation.
- Actor-scoped audit browsing through both interfaces.
- Versioned JSON save/load, startup recovery, and CLI heartbeat/autosave.
- Structured event and request logging, with optional rotating files.

## Architecture Overview

FleetFlow uses a hexagonal-style architecture. CLI and HTTP adapters invoke application workflows;
persistence, security, and event delivery sit behind ports. Domain rules are independent of these adapters.

```text
FleetFlow/
|-- data/                         # local runtime JSON files; generated, not source fixtures
|-- images/                       # project images/assets
|-- src/
|   |-- adapters/
|   |   |-- driven/
|   |   |   |-- events/           # in-process event dispatcher and structured event logging handler
|   |   |   |-- logging/          # stdout/file logging configuration
|   |   |   |-- persistence/database/ # PostgreSQL repositories, SQL, UoW, snapshots
|   |   |   |-- persistence/json/ # JSON world-state and user persistence
|   |   |   |-- persistence/memory/ # in-memory repositories, overview query, and runtime state gateway
|   |   |   `-- security/         # password hashing and JWT token services/configuration
|   |   `-- driving/
|   |       |-- cli/              # engine, menus, command factory, CLI commands
|   |       `-- http/             # FastAPI app, routers, schemas, request dependencies
|   |-- application/
|   |   |-- commands/             # immutable state-changing messages and typed routing keys
|   |   |-- dto/                  # persisted snapshot and runtime transfer objects
|   |   |-- enums/                # application-level classifications and reasons
|   |   |-- event_handlers/       # audit and other event consumers
|   |   |-- eventing/             # scopes, envelopes, collector, outbox contracts/codecs
|   |   |-- events/               # immutable application event definitions
|   |   |-- exceptions/           # application and world-state exception hierarchy
|   |   |-- messaging/            # message contracts, typed keys, scoped executors, and in-process buses
|   |   |-- models/               # persisted/query models such as UserRecord, AuditRecord, AuditLogQuery
|   |   |-- queries/              # immutable read messages and typed routing keys
|   |   |-- results/              # use-case/service result objects
|   |   |-- services/             # auth, fleet, heartbeat, reconciliation, snapshots
|   |   |   |-- audit_mapping/    # event-family audit mappings
|   |   |   `-- validators/       # world-state validation
|   |   `-- use_cases/            # auth, package, route, truck, customer, fleet, audit, and state workflows
|   |-- composition/              # container, event/message catalogs, subscriptions, and bus registration
|   |-- domain/
|   |   |-- entities/             # customers, packages, routes, trucks
|   |   |-- enums/                # roles, permissions, item/route/truck statuses
|   |   |-- events/               # immutable domain event definitions
|   |   |-- exceptions.py         # typed domain validation, not-found, and conflict errors
|   |   |-- services/             # map, route scheduling, and package/truck assignment policies
|   |   `-- value_objects/        # contact/location values, route paths/schedules, and assignment decisions
|   |-- ports/
|   |   |-- input/                # dispatch-only CommandBus and QueryBus protocols
|   |   `-- output/               # repositories, queries, UoW/outbox, persistence, runtime, event, and vehicle ports
|   `-- shared/                   # environment, JSON, event, and runtime-validation primitives
|-- tests/
|-- postman/                      # API collection, local environment, and runner notes
|-- cli_main.py                  # CLI entrypoint
|-- api_main.py                  # local API server entrypoint
`-- pyproject.toml
```

Both interfaces follow the same execution path:

```text
CLI command / HTTP router
  -> Bind actor and EventContext; build Command or Query
  -> CommandBus / QueryBus
  -> Registered use case, optionally wrapped in a scoped executor
  -> UseCase.execute(message)
  -> Application services, domain rules, and persistence ports
  -> EventCollector drains scoped application and tracked domain events
  -> InProcessEventDispatcher invokes subscribers
```

Buses use result-typed keys, enforce exact message types, and reject duplicate registrations or missing
handlers. Use cases implement `execute(message)` directly; there is no argument-adapting handler layer.

`EventDrainingExecutor` manages event-aware workflows. `WorldStateAdvancementExecutor` preserves heartbeat
domain-event-before-summary ordering. `WhoAmI` needs no event executor.

Composition entry points:

- `src/composition/container.py`: dependencies and backend selection.
- `src/composition/message_buses.py`: command/query registration.
- `src/composition/command_catalog.py` and `query_catalog.py`: message completeness catalogs.
- `src/composition/event_subscriptions.py`: logging and audit subscriptions.
- `src/composition/outbox_codecs.py`: current payload codec registration and registry builder.
- `src/composition/runtime.py`: cached dependencies shared by CLI and HTTP.

## Domain Model

- Entities: `Customer`, `DeliveryPackage`, `DeliveryRoute`, `Truck`.
- Values: `ContactInfo`, `LocationCode`, `RoutePath`, `RouteSchedule`, `RouteSegment`, `ScheduledStop`,
  `RoutePosition`, and package/truck assignment decisions.
- Services: `Map`, `RouteScheduler`, `RouteLoadCalculator`, `PackageAssignmentPolicy`, `TruckAssignmentPolicy`.

Supported hub codes:

```text
SYD, MEL, ADL, ASP, BRI, DAR, PER
```

`LocationCode` normalizes text to uppercase. `RoutePath` owns ordered, unique supported stops and their
position index; `Map` owns supported locations and intercity distances. Application `VehicleManager`
coordinates repository access and route/truck bindings, delegating suitability to the domain policy.

## Route, Truck, and Package Rules

- A route requires at least two unique supported stops. Its immutable schedule contains segments,
  arrival times, final ETA, total distance, and position lookups.
- A package's pickup and delivery stops must occur in that order. Assignment checks pickup progress,
  truck range, and capacity, then updates links and expected arrival. Reassignment to the same route is a no-op.
- Truck assignment checks range, capacity, schedule overlap, and location at availability time.
- Capacity means maximum simultaneous load on any route leg, not total package weight across the route.
- Detachment clears active package assignment state. Heartbeat reconciles statuses, locations, arrivals,
  and truck releases.

Shared validators live in `src/shared/validation.py`. Domain wrappers raise `DomainValidationError`;
application and persistence boundaries retain their own typed validation, not-found, and conflict errors.

## Events And Observability

Domain events describe customer, package, and route changes. Application events cover authentication,
authorization denial, reconciliation, and world-state operations. Each event has an ID, contract version,
naive app-local `occurred_at`, and UTC-aware `recorded_at`.

`EventContext` and `EventEnvelope` carry actor, source, correlation, and causation metadata. Each dispatch
has an `EventRecorderScope` for application events and tracked domain recorders. Domain checkpoints support
rollback of pending events. The collector clears recorders only after the publisher accepts the batch.

Subscribers are wired independently:

- Structured logging covers every type in `PUBLISHED_EVENT_TYPES`.
- Audit persistence covers events registered with `AuditDescriptorMapper`. Family-specific factories
  produce normalized descriptors; `AuditEventHandler` combines them with envelope metadata.
- Memory and PostgreSQL audit repositories support event-ID idempotency, filtering, stable ordering,
  pagination, and totals.

Publication is synchronous, after workflow persistence. Subscriber failures propagate after a successful
workflow; denial/failure events are published best-effort when the workflow itself raises, preserving the
original exception. A process crash between commit and publication can still lose events. The
[transactional outbox](#transactional-outbox) is not yet connected to runtime delivery.

## World-State Persistence

Default local paths:

| Path | Purpose | Override |
| --- | --- | --- |
| `data/users.json` | User records and password hashes | `JSON_USER_STORE_PATH` |
| `data/state.json` | Default save/load target | `JSON_STATE_PATH` |
| `data/exports/` | HTTP snapshot export/import boundary | `JSON_EXPORT_DIR` |

Bare filenames resolve under `data/`; relative paths with separators resolve from the project root.
Absolute paths remain absolute.

Snapshot schema version `2` contains repository ID counters, customers, packages, routes, and truck
runtime state. Both backends share this preparation pipeline:

```text
WorldStateSnapshot
  -> Validate schema, identities, references, compatibility, and customer contacts
  -> Rebuild and link a detached candidate world
  -> Reconcile route, package, and truck state
  -> ReconciledWorld
```

`WorldStateCorruptionError` preserves a reason through validation and event reporting:

- `MALFORMED_JSON`: invalid JSON.
- `INVALID_STRUCTURE`: invalid snapshot shape.
- `UNSUPPORTED_SCHEMA`: unsupported schema version.
- `INVALID_REFERENCES`: inconsistent IDs or links.
- `INVARIANT_VIOLATION`: invalid domain or runtime state.

In memory mode, saves serialize runtime repositories and the fleet. Loads prepare a candidate world and
swap repositories and truck state together. A failed swap restores the previous state and raises
`WorldStateRuntimeSwapError`.

Startup recovery runs when autosave is enabled. Missing state is ignored; corrupt state is quarantined
with a `.corrupt.<timestamp>` suffix. Other runtime errors propagate.

In PostgreSQL mode, exports load the world graph and sequence counters into the same snapshot format.
Imports prepare the candidate world, replace live logistics rows, update the fixed fleet, and reset ID
sequences. Autosave and default startup JSON loading are disabled; explicit save/load remains available.

Audit history uses a separate `audit_records` table with filtering and history indexes. Its `occurred_at`
remains app-local business time; `recorded_at` and `created_at` are UTC-aware system timestamps.

## Fleet Overview

`FleetOverviewQueryPort` uses one injected business timestamp for all deadline and position calculations.
The result includes:

- Package counts by `TODO`, `IN_PROGRESS`, and `DONE`, plus unassigned and past-due work.
- Route counts by `PLANNED`, `SCHEDULED`, `IN_PROGRESS`, and `COMPLETED`, plus past-due work.
- Free, assigned, and unknown-location truck counts.
- Active routes with positions, package counts, maximum segment loads, trucks, and capacity utilization.

The memory adapter materializes each entity collection once. PostgreSQL uses a read-only `REPEATABLE READ`
transaction and paginates candidates before fetching their packages. Both reconstruct schedule positions
and order active routes by next ETA, then route ID, with missing ETAs last.

Managers and employees have `FLEET_OVERVIEW_VIEW`. The active-route limit defaults to `10`, with bounds `1..100`:

```text
getfleetoverview [active_route_limit]
GET /api/fleet/overview?active_route_limit=10
```

## Authentication and Authorization

`MANAGER` has full access; `EMPLOYEE` has day-to-day logistics access without unrestricted administrative
or state-management permissions. Denial events record the attempted operation and target; actor identity
comes from the envelope.

If the active user repository has no `admin`, startup prompts for an initial manager password and
confirmation. There is no default password. Non-interactive startup without an admin fails.

The memory backend uses `users.json`; PostgreSQL uses its `users` table. Switching backends does not
migrate accounts, so each store needs its own admin bootstrap or existing account.

Passwords use PBKDF2-HMAC. HTTP uses access and refresh JWTs signed with separate secrets. Password
changes, manager resets, and HTTP logout increment the persisted token version to revoke existing tokens.
Refresh tokens are not stored server-side, and the `jti` claim alone does not provide revocation.

Typed validation, authentication, not-found, conflict, and persistence errors are mapped centrally to
HTTP responses. Invalid credentials return `401`, malformed persisted auth data returns `400`, duplicate
usernames return `409`, and database failures return sanitized `500` responses.

## Running the App

### Prerequisite

- Python 3.13 or later.

### Optional virtual environment

Run from the repository root. Create and activate a virtual environment:

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install runtime dependencies:

```bash
python -m pip install -e .
```

For development and testing, install the optional tools instead:

```bash
python -m pip install -e ".[dev]"
```

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

Edit the ignored `.env` file for your backend, database, JWT secrets, and logging settings.

Without `PERSISTENCE_BACKEND`, the default is `memory`. The example selects `postgres`; change it to
`memory` for local operation without a database, or supply PostgreSQL settings:

```text
PERSISTENCE_BACKEND=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fleetflow
DB_USER=<username>
DB_PASSWORD=<password>
```

For a new database, apply `src/adapters/driven/persistence/database/schema.sql`. For an existing database,
apply pending scripts in `src/adapters/driven/persistence/database/migrations/` in numeric order.
Startup seeds the fixed fleet when the trucks table is empty.

HTTP token issuance requires two different random secrets, each at least 32 characters:

```text
# Generate each secret independently with: openssl rand -hex 32
JWT_ACCESS_SECRET=<random access-token secret, at least 32 characters>
JWT_REFRESH_SECRET=<different random refresh-token secret, at least 32 characters>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

Do not use human-chosen phrases. Algorithm and expiry settings default to the values shown.

### Logging

Both entrypoints configure stdout logging. Set `LOG_FILE` to also write rotating files:

```text
LOG_LEVEL=INFO
LOG_FILE=logs/fleetflow.log
```

Levels: `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`, `NOTSET`. Files rotate at 10 MiB with five backups.

Logs cover startup, workflows, persistence, HTTP method/path/status/duration, and event-envelope metadata.
Passwords, JWTs, and database query parameters are not intentionally logged.

### Windows PowerShell

```powershell
python cli_main.py
```

### macOS / Linux

```bash
python cli_main.py
```

If imports fail in your environment, run from the repository root and set `PYTHONPATH` explicitly:

```powershell
$env:PYTHONPATH = "."
python cli_main.py
```

```bash
PYTHONPATH=. python cli_main.py
```

### HTTP API

Run the API locally with:

```powershell
python api_main.py
```

or:

```bash
python -m uvicorn src.adapters.driving.http.app:app --reload
```

The API is mounted under `/api`. Interactive OpenAPI docs are available at:

```text
http://127.0.0.1:8000/docs
```

## CLI Surface

### Menu-driven flows

The menu groups Packages, Routes, Trucks, Customers, State, Audit Logs, and Fleet Overview.
Authentication actions include Login, Logout, Who am I, Register user, and Change password.
Enter `cmd` for command mode.

### Command mode

| Area | Commands |
| --- | --- |
| Packages | `createpackage`, `viewpackage`, `viewallpackages`, `viewunassignedpackages`, `removepackage` |
| Routes | `createroute`, `viewroute`, `viewallroutes`, `viewroutesinprogress`, `removeroute` |
| Assignment | `assignpackagestoroute`, `findsuitableroutesforpackage`, `assigntrucktoroute`, `findsuitabletrucksforroute` |
| Fleet/customers | `viewalltrucks`, `viewallcustomers`, `getfleetoverview` |
| Authentication | `login`, `logout`, `whoami`, `registeruser`, `changepassword`, `resetpassword` |
| State/audit | `save`, `load`, `viewauditlogs` |

Examples:

```text
createpackage SYD MEL 10 "Jane Doe" jane@example.com 0412345678
createroute SYD MEL 2030-09-12 06:00
createroute SYD MEL ADL
assignpackagestoroute 1 4 5 6
assigntrucktoroute 1001 1
findsuitableroutesforpackage 4
findsuitabletrucksforroute 1
viewpackage 4
viewroute 1
viewauditlogs --limit 50 --total
getfleetoverview 10
save state.json
load state.json
login admin
changepassword
resetpassword employee
logout
```

Command mode uses shell-style parsing; quote arguments containing spaces.

## HTTP API Surface

- `POST /api/auth/login`
- `POST /api/auth/register`
- `POST /api/auth/change-password`
- `POST /api/auth/users/{username}/reset-password`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/customers/`
- `POST /api/packages`
- `GET /api/packages`
- `GET /api/packages/unassigned`
- `GET /api/packages/{package_id}`
- `GET /api/packages/{package_id}/suitable-routes`
- `DELETE /api/packages/{package_id}`
- `POST /api/routes/`
- `GET /api/routes/`
- `GET /api/routes/in-progress`
- `GET /api/routes/{route_id}`
- `DELETE /api/routes/{route_id}`
- `PATCH /api/routes/{route_id}/packages`
- `PATCH /api/routes/{route_id}/truck`
- `GET /api/routes/{route_id}/suitable-trucks`
- `GET /api/trucks/`
- `POST /api/state/save`
- `POST /api/state/load`
- `GET /api/audit/`
- `GET /api/fleet/overview`

Login accepts OAuth2 form data (`application/x-www-form-urlencoded`), not JSON:

```text
username=<username>
password=<password>
```

Login and refresh return:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

Send authenticated requests with `Authorization: Bearer <access_token>`.

Customer, package, unassigned-package, and all-route lists accept `limit`, `offset`, and `include_total`:

```text
GET /api/customers/?limit=50&offset=0
GET /api/packages/unassigned?limit=50&offset=0&include_total=true
```

`include_total` defaults to `false`, avoiding the count query and returning `"total": null`.
Routes in progress remain unpaginated and include computed positions.

Audit queries support pagination, exact event/resource/action/actor/source filters, and inclusive
occurrence and creation-time bounds:

```text
GET /api/audit/?limit=50&offset=0&include_total=true
GET /api/audit/?resource_type=package&resource_id=4&action=created
GET /api/audit/?actor_user_id=2&source=HTTP&occurred_from=2025-01-01T00:00:00
```

Managers with `AUDIT_VIEW` can browse all matching records. Employees are always scoped to their own user
ID. For employees, an explicitly supplied actor ID or username must match the current principal; no username
filter is added when omitted.

Fleet overview accepts `active_route_limit` (default `10`, range `1..100`) and returns nested summaries and
active routes with `at_stop` or `in_transit` positions. State save/load endpoints export/import JSON snapshots
for either backend.

HTTP error mappings:

| Status | Meaning |
| --- | --- |
| `400` | Application/domain validation failure |
| `401` | Invalid credentials or invalid, expired, revoked, or malformed token |
| `403` | Missing permission |
| `404` | Resource not found |
| `409` | Duplicate username or conflicting domain state |
| `422` | FastAPI body, form, path, or query validation failure |
| `500` | Persistence failure, with sanitized details |

## Autosave and Heartbeat

The CLI runs heartbeat/reconciliation around command execution. Mutating commands trigger autosave in
memory mode; PostgreSQL mutations persist directly, with explicit save/load reserved for snapshots.

Heartbeat and autosave dispatch through the command bus under the surrounding CLI event context,
preserving the user's actor and correlation ID.

## Testing

Tests cover domain rules, application workflows, bus composition, codecs, CLI/HTTP adapters, persistence,
snapshots, and runtime swaps. Run with pytest:

```bash
python -m pytest -q
```

Or use unittest with the project's `*_test.py` naming convention:

```bash
python -m unittest discover -v -s ./tests -t . -p "*_test.py"
```

Both commands work in PowerShell. Database tests use injected boundaries; a live PostgreSQL integration
harness is still pending.

### Postman / Newman

The `postman/` directory contains the API collection, local environment, and [runner notes](postman/README.md).
Start the API, set `adminPassword` in the environment, and run the collection in order to retain tokens and IDs:

```powershell
npx newman run "postman/FleetFlow API.postman_collection.json" `
  -e "postman/FleetFlow local.postman_environment.json"
```

```bash
npx newman run "postman/FleetFlow API.postman_collection.json" \
  -e "postman/FleetFlow local.postman_environment.json"
```

Coverage includes authentication, authorization, revocation, logistics, state import/export, and validation.
Controlled database-failure paths are tested in the unit suite.

## Tooling

`pyproject.toml` configures Ruff, Pyright, Mypy, and Pytest. Install the development dependencies before running:

```bash
python -m ruff check .
python -m pyright
python -m mypy .
```

## Roadmap

The CLI/API, both persistence backends, fleet overview, and audit browsing are implemented.
The main unfinished infrastructure is durable event delivery through the transactional outbox.

### Backend hardening

Add a live PostgreSQL integration-test harness and repeatable setup/migration workflows.

### Typed messaging and execution

Typed buses and scoped executors are implemented. Further work could add dispatch metrics, tracing,
transaction coordination, and targeted retries without duplicating logic in adapters.

### HTTP API expansion

Broaden integration coverage and tighten response-contract consistency.

### PostgreSQL persistence adapter

Add operational migration tooling and snapshot backup/restore safeguards.

### Audit log and domain events

Audit capture and browsing are implemented. Durable publication must preserve actor attribution,
causal ordering where required, and subscriber idempotency.

### Transactional outbox

Implemented:

- Validated draft/message models with UTC lifecycle timestamps, retry state, and claim-token leases.
- Transaction-bound insertion and worker-facing delivery repository ports.
- Current payload codecs for all 41 published events, grouped by event family.
- Explicit composition registration, a fresh-registry builder, and catalog-completeness tests.

`EventOutboxCodecRegistry` separates current encoders from historical readers. Writes use
`registry.for_event(event).encode(event)` to validate JSON and a lossless decode round trip. Reads resolve
the exact `(event_type, event_version)` through `for_identity()`; unknown versions never fall back.
Historical readers are not implemented, and old rows must not be relabeled with newer versions.
Payload containers remain mutable and must not be modified after validation and before persistence.

Remaining work:

1. Implement envelope serialization and the outbox table/migration.
2. Implement PostgreSQL and memory repository adapters.
3. Persist captured events in the same transaction as business state.
4. Add a worker with leased claims, retries, and ownership-checked acknowledgements.
5. Verify concurrency, duplicate delivery, and crash recovery against PostgreSQL before switching runtime publication.

### Background jobs

Consider a PostgreSQL-backed job table for bulk imports, reports, or scheduled work before adding an external queue.

### Fleet overview and reporting

Build on the overview query port for historical trends, SLA summaries, depot grouping, and dashboards.
Add caching or materialized views only when query costs justify them.

### Advanced logistics features

Possible extensions: route optimisation, delay prediction, notifications, driver/depot management,
proof of delivery, and real-time tracking.

## License

MIT
