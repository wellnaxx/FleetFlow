# FleetFlow

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/Interface-CLI%20%2B%20HTTP-0F766E)
![Architecture](https://img.shields.io/badge/Architecture-Hexagonal--style-8B5CF6)
![Tests](https://img.shields.io/badge/Tests-pytest%20%2B%20unittest-2563EB)

FleetFlow is a logistics management system for packages, delivery routes, trucks, customers, and authenticated users across Australian freight hub locations. It currently exposes an interactive CLI and a FastAPI HTTP adapter. The internals are structured around domain entities, application use cases, typed messaging contracts, services, ports, adapters, and a composition root so workflows can be reused by multiple driving adapters.

## Capabilities

FleetFlow currently supports:

- Interactive menu-driven operation and command-mode workflows.
- FastAPI HTTP adapter with authentication plus customer, package, route, truck, fleet-overview,
  audit-log, and world-state workflows.
- Package creation, lookup, removal, unassigned-package listing, and route assignment.
- Route creation, lookup, removal, in-progress tracking, package assignment, and truck assignment.
- Truck fleet management with deterministic city dispersion.
- Authorized point-in-time fleet overviews containing package, route, and truck counts; overdue and
  unassigned work; and ordered active-route details with schedule-derived positions, segment loads,
  assigned trucks, and capacity utilization.
- Pure package and truck assignment policies with structured acceptance/rejection decisions.
- Truck suitability checks for start-location compatibility, route range, time-window availability, availability-location transitions, and carrying capacity.
- A reusable route-load calculator for segment-based capacity validation and fleet reporting, so truck
  capacity is evaluated against the maximum simultaneous load on a route leg rather than total package
  weight across the whole route.
- Immutable, validated route paths and schedules with indexed location and arrival lookups.
- Customer records derived from package creation, including email and phone lookup indexes.
- User authentication with manager and employee roles.
- JWT access/refresh tokens for HTTP authentication, with token-version revocation.
- Typed domain, application, and repository errors for expected validation, not-found, conflict, authentication, and persistence failures.
- Centralized layer-neutral runtime validation with domain and adapter wrappers that preserve boundary-specific errors.
- Typed command/query messages, routing keys, dispatch input-port protocols, and thin handlers covering the
  current interactive workflows. Synchronous in-process command and query buses are implemented;
  composition-owned registration and adapter migration remain in progress, so CLI and HTTP currently continue to
  invoke use cases directly.
- Global FastAPI exception handlers that map expected application/domain failures to stable, sanitized HTTP responses.
- Immutable domain and application event types with per-entity/use-case pending-event recording, event checkpoints for rollback, context-local envelope metadata, synchronous in-process dispatch, and structured event logging.
- Browsable audit log with normalized descriptors, versioned event payloads, subscribed persistence handlers, in-memory and PostgreSQL repositories, and actor-scoped CLI/HTTP queries.
- Role-based authorization around CLI commands and application use cases.
- Password hashing with PBKDF2-HMAC and strict persisted password-hash validation.
- Configurable application logging to stdout and optional rotating log files, including HTTP request duration/status logging.
- Environment-selected in-memory or PostgreSQL logistics persistence backend.
- Manual save/load plus autosave after mutating commands when autosave is enabled.
- Versioned JSON world-state snapshots containing customers, packages, routes, repository counters, and truck runtime state.
- Reasoned world-state corruption handling that distinguishes malformed JSON, invalid structure, unsupported schema, invalid references, and invariant violations.
- PostgreSQL world-state export/import through the same JSON snapshot format.
- Startup recovery for default saved state: missing state is ignored, corrupt state is quarantined, and unexpected runtime errors still fail loudly.
- A Postman/Newman collection covering authentication, authorization, logistics workflows, state import/export, validation, and token revocation.
- A large automated test suite covering domain behavior, application services, use cases, typed command/query
  handlers, CLI commands, HTTP routers/dependencies, fleet-overview composition and projections, JSON and
  database persistence, runtime swaps, snapshot import/export, and startup behavior.

## Architecture Overview

FleetFlow uses a hexagonal-style layered architecture. The CLI and HTTP API are driving adapters. JSON world-state persistence, in-memory repositories, PostgreSQL repositories, security, and runtime state management are driven adapters behind application-level ports and services.

```text
FleetFlow/
|-- data/                         # local runtime JSON files; generated, not source fixtures
|-- images/                       # project images/assets
|-- src/
|   |-- adapters/
|   |   |-- driven/
|   |   |   |-- events/           # in-process event dispatcher and structured event logging handler
|   |   |   |-- logging/          # stdout/file logging configuration
|   |   |   |-- persistence/database/ # PostgreSQL repositories, overview queries, SQL, graph loaders, UoW, snapshots
|   |   |   |-- persistence/json/ # JSON world-state and user persistence
|   |   |   |-- persistence/memory/# in-memory repositories, overview query, and runtime state gateway
|   |   |   `-- security/         # password hashing and JWT token services/configuration
|   |   `-- driving/
|   |       |-- cli/              # engine, menus, command factory, CLI commands
|   |       `-- http/             # FastAPI app, routers, schemas, request dependencies
|   |-- application/
|   |   |-- commands/             # immutable state-changing messages and typed routing keys
|   |   |-- dto/                  # persisted snapshot and runtime transfer objects
|   |   |-- enums/                # application-level classifications and reasons
|   |   |-- event_handlers/       # audit and other event consumers
|   |   |-- eventing/             # collector, execution context, event envelopes, handler protocol
|   |   |-- events/               # immutable application event definitions
|   |   |-- exceptions/           # application and world-state exception hierarchy
|   |   |-- handlers/             # thin command/query adapters over existing use cases
|   |   |-- messaging/            # message markers, typed keys, and handler protocols
|   |   |-- models/               # persisted/query models such as UserRecord, AuditRecord, AuditLogQuery
|   |   |-- queries/              # immutable read messages and typed routing keys
|   |   |-- results/              # use-case/service result objects
|   |   |-- services/             # auth, authorization, fleet orchestration, heartbeat, reconciliation, snapshot services
|   |   |   |-- audit_mapping/    # typed event-to-audit registry and mappings grouped by event family
|   |   |   `-- validators/       # focused world-state schema, identity, reference, truck, and compatibility validators
|   |   `-- use_cases/            # auth, package, route, truck, customer, fleet, audit, and state workflows
|   |-- composition/              # dependency container, event catalog, subscriptions, and composition root
|   |-- domain/
|   |   |-- entities/             # customers, packages, routes, trucks
|   |   |-- enums/                # roles, permissions, item/route/truck statuses
|   |   |-- events/               # immutable domain event definitions
|   |   |-- exceptions.py         # typed domain validation, not-found, and conflict errors
|   |   |-- services/             # map, route scheduling, and package/truck assignment policies
|   |   `-- value_objects/        # contact/location values, route paths/schedules, and assignment decisions
|   |-- ports/
|   |   |-- input/                # dispatch-only CommandBus and QueryBus protocols
|   |   `-- output/               # repositories, fleet/audit queries, persistence, runtime, event, and vehicle ports
|   `-- shared/                   # environment, JSON, event, and runtime-validation primitives
|-- tests/
|-- postman/                      # API collection, local environment, and runner notes
|-- cli_main.py                  # CLI entrypoint
|-- api_main.py                  # local API server entrypoint
`-- pyproject.toml
```

The CLI runtime flow is:

```text
CLI Menu / Command Mode
  -> Bind CLI EventContext
  -> CLI Command
  -> Application Use Case
  -> Application Service / Port
  -> Domain Entity / Domain Service
  -> In-memory/PostgreSQL Repository or JSON Persistence Adapter
  -> EventCollector drains pending events
  -> In-process EventDispatcher invokes subscribers
```

The HTTP runtime flow is:

```text
FastAPI Router
  -> Request Dependency / Authenticated Principal / EventContext
  -> Application Use Case
  -> Application Service / Port
  -> Domain Entity / Domain Service
  -> In-memory/PostgreSQL Repository or JSON Persistence Adapter
  -> EventCollector drains pending events
  -> In-process EventDispatcher invokes subscribers
```

These diagrams describe the currently wired runtime. The application also contains the first command/query
bus migration slice: immutable messages, result-typed routing keys, structural handler contracts, dispatch-only
input ports, and thin handlers that adapt messages to existing use-case signatures. The in-process command and
query buses support exact-type dispatch, name-based routing, duplicate-registration protection, and unchanged
handler error propagation. Composition-owned registration remains unfinished, so CLI and HTTP adapters do not
dispatch through this layer yet.

The intended next-stage flow is:

```text
CLI Command / FastAPI Router
  -> CommandBus or QueryBus
  -> Typed CommandHandler or QueryHandler
  -> Existing Application Use Case
  -> Application Service / Output Port / Domain
```

The composition root is `src/composition/container.py`. It wires repositories, domain services, application services, world-state persistence, runtime state management, the event collector, and use-case registries. `src/composition/runtime.py` provides cached runtime dependencies shared by the CLI and HTTP adapters. Event subscriptions are centralized in `src/composition/event_subscriptions.py`.

## Domain Model

FleetFlow models:

- `Customer`
- `DeliveryPackage`
- `DeliveryRoute`
- `Truck`
- `ContactInfo`
- `LocationCode`
- `RoutePath`
- `RouteSchedule`, `RouteSegment`, `ScheduledStop`, and `RoutePosition`
- `PackageAssignmentDecision` and `TruckAssignmentDecision`
- `Map`
- `RouteScheduler`
- `RouteLoadCalculator`
- `PackageAssignmentPolicy` and `TruckAssignmentPolicy`

The application layer also provides `VehicleManager`, which coordinates truck
repository access and runtime route/truck binding replacement while delegating
suitability decisions to the pure domain policy.

Supported hub codes are:

```text
SYD, MEL, ADL, ASP, BRI, DAR, PER
```

`LocationCode` normalizes location text to uppercase. `RoutePath` owns the
ordered, unique set of supported stops and its immutable position index. `Map`
owns the supported location set and intercity distances.

## Route, Truck, and Package Rules

FleetFlow enforces the main logistics invariants in the domain and application layers:

- `RoutePath` normalizes raw route stops and requires at least two unique,
  supported locations.
- Packages can only be assigned to routes that contain their start and end locations in the correct order.
- `RouteScheduler` builds an immutable `RouteSchedule` from a validated path, containing ordered segments, stop times, final ETA,
  total distance, and indexed arrival/position lookups.
- `PackageAssignmentPolicy` returns a structured acceptance or rejection decision for route compatibility,
  pickup progress, truck range, and maximum segment load.
- `RouteLoadCalculator` derives per-segment package loads and the maximum simultaneous route load without
  requiring route hydration solely for reporting calculations.
- Package assignment updates package-route links and expected arrival when possible, while reassignment to the
  same route remains idempotent.
- Removing a package from a route clears its active assignment state.
- `TruckAssignmentPolicy` returns a structured decision for range, maximum
  segment load, immediate location, schedule overlap, and the location where an
  already assigned truck becomes available.
- Application `VehicleManager` performs fleet repository access and binding
  replacement without owning assignment policy rules.
- Carrying capacity is checked by maximum segment load rather than total assigned package weight.
- Heartbeat/reconciliation updates route statuses, truck positions, truck releases, package statuses, package current locations, and expected arrivals.

Expected domain failures use typed exceptions. Reusable primitive validation for
integers, strings, datetimes, UUIDs, and finite positive numbers lives in
`src/shared/validation.py`; domain adapters translate those failures into
`DomainValidationError`, while persistence and application boundaries retain
their own error contracts. Validation problems, missing domain entities, and
conflict/business-rule failures are translated by application use cases and
global HTTP exception handlers into stable CLI/API-facing messages instead of
relying on raw `ValueError` text.

## Events And Observability

FleetFlow has an in-process event pipeline for business facts and application workflows.

- Domain entities record pending events for customer, package, and route lifecycle changes, including creation, assignment, detachment, pickup, delivery, scheduling, truck assignment/release, route start/completion, and removal.
- Event-aware use cases record authentication, authorization denial, heartbeat, world-state import/export, and world-state corruption events. Authorization denials retain the attempted operation, target resource, target id, and missing permissions.
- Events are immutable and share an event id, positive per-event contract version, business `occurred_at` timestamp, and UTC `recorded_at` timestamp. Audit records preserve the version used to serialize each event.
- Event checkpoints allow pending events to be rolled back with failed in-memory mutations.
- `EventContext`, `EventActor`, and `EventEnvelope` provide correlation, source, actor, and causation metadata through `ContextVar`-local workflow context.
- CLI commands and HTTP router handlers bind event context before draining pending events. CLI heartbeat and autosave events are drained under the surrounding CLI command context.
- `EventCollector` captures pending events from use cases and entities, wraps them with the current context, publishes them, and clears recorders only after the publisher accepts the batch.
- `InProcessEventDispatcher` routes envelopes by exact event type to subscribed handlers.
- `PUBLISHED_EVENT_TYPES` is the exhaustive composition-level event catalog used to subscribe structured logging independently of audit coverage.
- `StructuredEventLoggingHandler` is subscribed to every cataloged event type and writes event metadata to the configured application logger.
- `AuditDescriptorMapper` performs exact-type lookup through an immutable typed registry. Explicit descriptor factories are grouped by auth, customer, package, route, startup, world-state, and reconciliation event families.
- `AuditEventHandler` receives that mapper through composition, combines an event envelope with its normalized descriptor, and persists an `AuditRecordDraft` through `AuditRepositoryPort`.
- In-memory and PostgreSQL audit repositories implement the audit repository contract, including idempotency by event id, filtering, stable ordering, pagination, and page-total queries. The CLI and HTTP API expose those queries with manager-wide and employee self-only authorization.

Events are currently dispatched synchronously in process after workflow persistence completes. The runtime subscription graph wires structured logging from the independent published-event catalog and audit persistence from registered audit mappings. Handler failures are not isolated: an audit repository failure propagates as event-publication failure. FleetFlow does not yet include a transactional outbox, so event handling is still not resilient to process crashes between business-state commit and handler execution.

## World-State Persistence

FleetFlow stores local JSON files under the repository's `data/` directory by default:

- `data/users.json`: persisted user records and password hashes.
- `data/state.json`: default world-state save/load target.
- `data/exports/`: default HTTP snapshot export/import boundary.

These paths can be overridden with:

```text
JSON_USER_STORE_PATH=<path>
JSON_STATE_PATH=<path>
JSON_EXPORT_DIR=<path>
```

Bare filenames such as `state.json` and `users.json` resolve under `data/`. Relative paths containing directory separators resolve from the project root, and absolute paths remain absolute.

World-state saves are versioned snapshots. The current canonical schema version is `2` and includes:

- repository id counters,
- customers,
- packages,
- routes,
- truck runtime snapshots.

The application-level snapshot preparation pipeline is shared by the in-memory and PostgreSQL backends:

```text
WorldStateSnapshot
  -> schema, identity, reference, truck, compatibility, and customer validation
  -> rebuild detached candidate world
  -> link package/route/truck relationships
  -> reconcile route, package, and truck runtime state
  -> produce ReconciledWorld
```

Snapshot corruption is represented by `WorldStateCorruptionError` with one stable reason:

- `MALFORMED_JSON`: the source is not valid JSON.
- `INVALID_STRUCTURE`: the JSON or versioned snapshot shape is invalid.
- `UNSUPPORTED_SCHEMA`: the snapshot declares a schema version FleetFlow does not support.
- `INVALID_REFERENCES`: ids or bidirectional links between snapshot records do not agree.
- `INVARIANT_VIOLATION`: structurally valid data violates domain or runtime-state rules.

`WorldStateSnapshotValidator` orchestrates focused validators for schema, identity/counters, references, truck runtime state, route/package and truck/route compatibility, and customer contact uniqueness. The same reason is preserved through rebuilding, linking, and reconciliation so `LoadWorldStateUseCase` can record `WorldStateCorruptionDetected` and `WorldStateImportFailed` pending application events without parsing error text.

For the in-memory backend:

```text
Save:
In-memory runtime repositories + truck fleet
  -> WorldStateSnapshotService.build_snapshot()
  -> JsonWorldStatePersistence.write()

Load:
JsonWorldStatePersistence.read()
  -> WorldStateSnapshotService.apply_snapshot()
  -> validate snapshot schema and graph invariants
  -> rebuild candidate world
  -> reconcile candidate world
  -> InMemoryWorldStateRuntime.replace_world_state()
```

Runtime replacement is performed through a single world-state swap boundary so repositories and truck runtime state are committed together. If a valid snapshot cannot be committed to runtime, the previous runtime state is restored and a `WorldStateRuntimeSwapError` is raised.

At startup, FleetFlow attempts to load the default state file when autosave is enabled. Missing default state is treated as a no-op. Corrupt world-state JSON is quarantined with a `.corrupt.<timestamp>` suffix and the application starts with empty runtime state. Non-corruption runtime errors are not swallowed.

For the PostgreSQL backend:

```text
Save:
PostgreSQL world graph loader + sequence counter loader
  -> WorldStateSnapshotBuilder
  -> JsonWorldStatePersistence.write()

Load:
JsonWorldStatePersistence.read()
  -> PostgresWorldStateGateway.apply_snapshot()
  -> shared snapshot preparation pipeline
  -> PostgresWorldStateImporter.import_world()
  -> clear live world tables, insert customers/routes/packages, update fixed fleet trucks, reset id sequences
```

When `PERSISTENCE_BACKEND=postgres`, package, route, truck, customer, user, authentication, audit,
fleet-overview query, and unit-of-work operations have PostgreSQL adapters. Autosave and default startup
JSON loading are disabled for this backend, but explicit `save` and `load` commands are available as
snapshot export/import operations. PostgreSQL snapshot import/export is covered by unit tests and a
gateway-level round-trip integration test with injected database boundaries; a live PostgreSQL test
harness is still future infrastructure work.

The PostgreSQL schema also includes `audit_records` plus indexes for event idempotency, resource history, actor history, event type, action, source, occurrence time, creation time, and correlation id. Audit timestamps intentionally distinguish app-local business time (`occurred_at`) from UTC system timestamps (`recorded_at` and `created_at`).

Audit records are written by the in-process event subscription graph and can be browsed through the `viewauditlogs` CLI command or the HTTP audit endpoint. Managers with `AUDIT_VIEW` can query the full history; employees are restricted to records attributed to their own actor identity.

## Fleet Overview

FleetFlow exposes a read-only, cross-aggregate fleet overview through both persistence backends. The
application use case obtains one app-local business timestamp from the injected container clock and passes
that timestamp to the active `FleetOverviewQueryPort`, ensuring package deadlines, route deadlines, and
active-route positions are evaluated against the same point in time.

The overview contains:

- package counts by `TODO`, `IN_PROGRESS`, and `DONE`, plus unassigned and past-due counts;
- route counts by `PLANNED`, `SCHEDULED`, `IN_PROGRESS`, and `COMPLETED`, plus past-due counts;
- free, assigned, and unknown-location truck counts;
- a bounded, ordered collection of active routes;
- each active route's persisted status, start/end locations, schedule-derived at-stop or in-transit
  position, assigned package count, maximum segment load, assigned truck, and capacity utilization.

The in-memory adapter materializes each repository collection once and calculates all metrics for that
entity family from the same collection. The PostgreSQL adapter runs aggregate and active-route queries in a
read-only `REPEATABLE READ` transaction, validates returned rows, bounds active-route candidates before
loading package rows, reconstructs schedule-dependent positions in the domain layer, and retains the same
next-ETA/route-id ordering as the memory adapter.

Both employees and managers currently receive `FLEET_OVERVIEW_VIEW`. Authorization failures are recorded
through the normal `AuthorizationDenied` event path. The driving-adapter entry points are:

```text
getfleetoverview [active_route_limit]
GET /api/fleet/overview?active_route_limit=10
```

The active-route limit defaults to `10` and must be from `1` through `100`.

## Authentication and Authorization

FleetFlow has two roles:

- `MANAGER`
- `EMPLOYEE`

Managers have full access. Employees can perform day-to-day logistics operations but do not have unrestricted administrative/state-management access.

Denied authorization decisions are recorded as application events with normalized operation and target metadata. Actor identity remains envelope context, avoiding duplication inside the event payload.

On first startup, if no `admin` user exists in the active user repository, FleetFlow creates the initial manager interactively. In memory mode this checks the configured JSON user store. In PostgreSQL mode this checks the PostgreSQL users table. It prompts for a password and confirmation:

```text
Create initial manager password:
Confirm initial manager password:
```

There is no hardcoded default admin password in the current version.

If the application is started non-interactively and no admin user exists, startup fails with a clear error telling you to run it interactively once.

User repositories are selected by `PERSISTENCE_BACKEND`. Existing `users.json` users are not visible when `PERSISTENCE_BACKEND=postgres`; switching to PostgreSQL requires existing rows in the PostgreSQL users table or one interactive startup to bootstrap the initial `admin` user into PostgreSQL. Switching back to memory mode uses `users.json` again.

HTTP authentication uses JWT access and refresh tokens signed with separate secrets. Tokens include the persisted user id, username, role, token version, and a `jti` claim. Password changes and manager password resets update the password hash and increment the user's token version atomically, so existing access and refresh tokens are rejected. HTTP logout also increments the user's token version. Refresh tokens are not stored server-side in this version, and `jti` values are reserved for future denylist or rotation support; `jti` does not provide revocation by itself.

Authentication failures are intentionally reported with safe messages. Invalid credentials return `401`, malformed persisted auth data returns `400`, duplicate usernames return `409`, and database failures return generic `500` responses without leaking adapter details.

Application use cases use typed error boundaries for expected failures:

- `ValidationError` and `DomainValidationError` for invalid command/request data or invalid domain state.
- `NotFoundError` and `EntityNotFoundError` for missing requested resources.
- `ConflictError` and `DomainConflictError` for operations that conflict with current state.
- `AuthenticationError` for failed authentication.

Global HTTP exception handlers map those errors to stable status codes and safe response details.

## Running the App

### Prerequisite

- Python 3.13

### Optional virtual environment

Create and activate a virtual environment before installing the project.

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

Install the project runtime dependencies before running the CLI or API:

```bash
python -m pip install -e .
```

For development, static analysis, and the full automated suite, install the optional development tools:

```bash
python -m pip install -e ".[dev]"
```

Create local configuration from the checked-in example:

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

Update `.env` with the selected persistence backend, database credentials, JWT secrets, and optional logging settings. The local `.env` file is ignored by Git.

When `PERSISTENCE_BACKEND` is absent, the application defaults to in-memory logistics repositories plus
JSON world-state persistence. The checked-in `.env.example` currently selects PostgreSQL; change its copied
value to `memory` for local in-memory operation, or configure the required database settings before using
the example's `postgres` value:

```text
PERSISTENCE_BACKEND=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fleetflow
DB_USER=<username>
DB_PASSWORD=<password>
```

Apply `src/adapters/driven/persistence/database/schema.sql` to a new database before using the PostgreSQL backend. For existing databases, apply the SQL scripts under `src/adapters/driven/persistence/database/migrations/` in numeric order. The composition root seeds the fixed fleet if the trucks table is empty.

HTTP JWT issuance requires a secret before login or refresh tokens can be created:

```text
# Generate each secret independently with: openssl rand -hex 32
JWT_ACCESS_SECRET=<random access-token secret, at least 32 characters>
JWT_REFRESH_SECRET=<different random refresh-token secret, at least 32 characters>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

`JWT_ACCESS_SECRET` and `JWT_REFRESH_SECRET` are required, must be different, and should be randomly generated rather than human-chosen phrases. The other JWT settings use the defaults shown above when omitted.

### Logging

Both `cli_main.py` and `api_main.py` configure standard Python logging at startup. Logs are always written to stdout. Set `LOG_FILE` to also write rotating log files:

```text
LOG_LEVEL=INFO
LOG_FILE=logs/fleetflow.log
```

Supported levels are `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`, and `NOTSET`. File logs rotate at 10 MiB with five retained backups. Omit `LOG_FILE` to log only to stdout.

Logging covers startup/composition, selected mutating use cases, CLI command execution, persistence operations, global HTTP failures, HTTP request method/path/status/duration, and published event-envelope metadata. Event logs include event type, event id, occurred/recorded timestamps, envelope id, correlation id, source, causation id, and actor identity when available. Passwords, JWTs, and database query parameters are not intentionally logged.

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

Every HTTP request is logged with its method, path, response status, and duration. Expected application/domain failures are handled centrally; persistence failures return generic details rather than exposing adapter or database errors.

## CLI Surface

### Menu-driven flows

The main menu exposes:

- Packages
- Routes
- Trucks
- Customers
- State
- Audit Logs
- Fleet Overview
- Command mode via `cmd`
- Login
- Logout
- Who am I
- Register user
- Change password

### Command mode

The command registry currently supports:

- `createpackage`
- `viewpackage`
- `viewallpackages`
- `viewunassignedpackages`
- `removepackage`
- `createroute`
- `viewroute`
- `viewallroutes`
- `viewroutesinprogress`
- `removeroute`
- `assignpackagestoroute`
- `findsuitableroutesforpackage`
- `assigntrucktoroute`
- `findsuitabletrucksforroute`
- `viewalltrucks`
- `viewallcustomers`
- `login`
- `logout`
- `whoami`
- `registeruser`
- `changepassword`
- `save`
- `load`
- `viewauditlogs`
- `getfleetoverview`

Examples:

```text
createpackage SYD MEL 10 "Jane Doe" jane@example.com 0412345678
createroute SYD MEL 2025-09-12 06:00
createroute SYD MEL ADL
assignpackagestoroute 1 4 5 6
assigntrucktoroute 1001 1
findsuitableroutesforpackage 4
findsuitabletrucksforroute 1
viewpackage 4
viewroute 1
viewallpackages
viewunassignedpackages
viewallroutes
viewroutesinprogress
viewalltrucks
viewallcustomers
viewauditlogs --limit 50 --total
getfleetoverview 10
save state.json
load state.json
login admin
whoami
changepassword admin
logout
```

Quoted arguments are supported in command mode through shell-style parsing, so names with spaces should be quoted.

## HTTP API Surface

The FastAPI adapter currently exposes:

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

Login uses OAuth2-style form data with content type `application/x-www-form-urlencoded`; it does not accept a JSON login body:

```text
username=<username>
password=<password>
```

Successful login and refresh responses return:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

Authenticated requests use:

```text
Authorization: Bearer <access_token>
```

Customer listing is paginated:

```text
GET /api/customers/?limit=50&offset=0
GET /api/customers/?limit=50&offset=0&include_total=true
```

Package listing uses the same pagination shape:

```text
GET /api/packages?limit=50&offset=0
GET /api/packages?limit=50&offset=0&include_total=true
GET /api/packages/unassigned?limit=50&offset=0
GET /api/packages/unassigned?limit=50&offset=0&include_total=true
```

Route listing also supports the same `limit`, `offset`, and `include_total` query parameters.

List-style use cases for customers, packages, unassigned packages, and all routes share the same `PageQuery` / `PageResult` pagination model and `execute_page_query` orchestration helper. `include_total` defaults to `false` so normal list requests do not run a count query. When omitted, the response contains `"total": null`. When requested, customer, package, and route page totals are loaded with the page from one repository operation.

Routes in progress intentionally remain unpaginated because the result is bounded by active truck assignments and includes computed route-position data:

```text
GET /api/routes/in-progress
```

Audit-log browsing supports pagination plus exact resource, action, actor, source, and event-type filters,
along with inclusive occurrence and creation-time bounds:

```text
GET /api/audit/?limit=50&offset=0
GET /api/audit/?limit=50&offset=0&include_total=true
GET /api/audit/?resource_type=package&resource_id=4&action=created
GET /api/audit/?actor_user_id=2&source=HTTP&occurred_from=2025-01-01T00:00:00
```

Managers with `AUDIT_VIEW` may browse all matching records. Employees are restricted by the application use
case to records attributed to their own user id and username.

Fleet overview accepts one bounded query parameter and returns a nested operational projection:

```text
GET /api/fleet/overview
GET /api/fleet/overview?active_route_limit=25
```

`active_route_limit` defaults to `10` and accepts values from `1` through `100`. The response contains a
single generation timestamp, package/route/truck summaries, computed category totals, and ordered active
routes with discriminated `at_stop` or `in_transit` position objects.

World-state endpoints act as JSON snapshot export/import operations. With the in-memory backend they save/load runtime state; with the PostgreSQL backend they export/import the database-backed world graph through the same snapshot format:

```text
POST /api/state/save
POST /api/state/load
```

Common HTTP error mappings are:

- `400 Bad Request` for application or domain validation failures.
- `401 Unauthorized` for invalid, expired, revoked, or malformed tokens and invalid login credentials.
- `403 Forbidden` for missing permissions.
- `404 Not Found` for requested resources that do not exist.
- `409 Conflict` for duplicate usernames or inconsistent domain state.
- `422 Unprocessable Entity` for FastAPI request-body, form-field, path, and query-parameter validation.
- `500 Internal Server Error` for persistence failures, reported with generic details.

## Autosave and Heartbeat

The CLI engine performs heartbeat/reconciliation around command execution. Reconciliation may update route status, truck position, truck release state, package status, package current location, and expected arrival.

Mutating commands are autosaved to the default world-state path when autosave is enabled. Autosave is enabled for the in-memory backend and disabled for the PostgreSQL backend. With PostgreSQL, `save` and `load` remain explicit snapshot export/import commands, but normal command mutations are persisted directly through database repositories and units of work.

Heartbeat and autosave run inside the current CLI command event context, so their application events share the command correlation id and actor when they are triggered by user-entered CLI work.

## Testing

The project supports both `pytest` and `unittest` discovery.

Recommended test command:

```bash
python -m pytest -q
```

The tests use the `*_test.py` naming convention, so plain `python -m unittest discover` will not find everything. Use:

```bash
python -m unittest discover -v -s ./tests -t . -p "*_test.py"
```

Windows PowerShell uses the same commands:

```powershell
python -m pytest -q
python -m unittest discover -v -s ./tests -t . -p "*_test.py"
```

### Postman / Newman

The `postman/` directory contains:

- `FleetFlow API.postman_collection.json`
- `FleetFlow local.postman_environment.json`
- setup and execution notes in `postman/README.md`

Start the API, configure `adminPassword` in the Postman environment, and run the collection in order so generated tokens and resource identifiers are retained. With Newman available through `npx`, run:

```powershell
npx newman run "postman/FleetFlow API.postman_collection.json" `
  -e "postman/FleetFlow local.postman_environment.json"
```

```bash
npx newman run "postman/FleetFlow API.postman_collection.json" \
  -e "postman/FleetFlow local.postman_environment.json"
```

The collection covers authentication, authorization, token revocation, customers, packages, routes, trucks, world-state import/export, and validation/error paths. Controlled database-failure paths remain unit-test responsibilities.

## Tooling


Static-analysis and formatting/lint configuration live in `pyproject.toml`.

Configured tools:

- Ruff
- Pyright
- Mypy
- Pytest

These are development tools and are not required to run the application.
Example commands, assuming the tools are installed:

```bash
python -m ruff check .
python -m pyright
python -m mypy .
```

## Roadmap

FleetFlow is currently a logistics backend with CLI and HTTP driving adapters, a layered/hexagonal
architecture, domain entities, immutable route path/schedule values, pure package/truck assignment
policies, use cases, ports, in-memory repositories, PostgreSQL repository/query adapters, a point-in-time
fleet overview, JSON world-state persistence, authentication, autosave/load support, heartbeat
reconciliation, segment-aware route capacity checks, audit browsing, and synchronous in-process event
publication.

The current architecture leaves several possible paths for future development. These are not required for the core project to work, but they are natural extensions if the project continues growing.

### Backend hardening

The existing backend can be tightened further by hardening PostgreSQL setup/migration workflows and adding a real PostgreSQL integration-test harness.

### Command bus layer

FleetFlow now has immutable command/query messages for the current interactive workflows, typed routing keys,
structural handler protocols, dispatch-only `CommandBus` and `QueryBus` input ports, and thin handlers that adapt
those messages to existing use cases. Handler tests verify argument forwarding, result propagation, and the few
temporary representation conversions required by current use-case signatures.

The synchronous command and query buses are implemented and tested with routing-name identity, exact message-type
checks, duplicate-registration rejection, missing-handler reporting, and unchanged handler result/error
propagation. The remaining work is to register every key/handler pair in composition and migrate CLI and HTTP
adapters from direct use-case calls to typed dispatch. Once that path is stable, repeated cross-cutting behavior
such as event draining, logging, metrics, and transaction boundaries can move into a small bus pipeline.
Straightforward handler/use-case pairs can then be merged where the separate adapter no longer adds value. The
heartbeat-only world-state advancement workflow remains an internal orchestration path rather than a public
command.

### HTTP API expansion

The current FastAPI adapter covers authentication, customer listing, package workflows, route workflows,
truck listing, fleet overview, world-state import/export, and actor-scoped audit-log browsing. Remaining
HTTP work is general hardening, broader integration coverage, and further response-contract consistency.

### PostgreSQL persistence adapter

The current PostgreSQL adapter sits behind repository/query ports for package, route, truck, customer,
user, audit, fleet-overview, and unit-of-work persistence. It gives FleetFlow a more realistic long-running
backend while preserving the CLI and application use-case boundaries.

Remaining work includes operational migration tooling, stronger integration coverage against a real database, and production hardening for snapshot import/export workflows such as backup/restore procedures and operational safeguards.

### Audit log and domain events

FleetFlow already defines and records pending domain and application events for important actions such as package assignment, route scheduling, truck dispatch/release, package delivery, authentication, authorization denial, heartbeat advancement, and world-state import/export. Event envelopes and context metadata are available for correlation and actor attribution, and the in-process dispatcher currently publishes those envelopes to structured logging and audit handlers.

The audit-log model, typed exact-event descriptor registry, family-specific descriptor factories, audit handler, repository port, in-memory repository, PostgreSQL repository, SQL queries, schema migrations, composition wiring, query use case, CLI command, and HTTP endpoint are implemented. Logging subscriptions are driven by an independent exhaustive event catalog, while audit subscriptions are driven by registered mappings. The active repository follows the configured persistence backend. Manager-wide and employee self-only filtering is enforced in the application use case. The current failure policy is strict: audit handler or repository failures propagate to the publisher.

The next eventing reliability step is to unify mutating persistence under explicit unit-of-work boundaries, separate event capture from publication, and add live PostgreSQL transaction coverage. A transactional outbox can then persist versioned event envelopes in the same transaction as business state before asynchronous dispatch. External brokers such as Kafka or Redis Streams would only make sense later if the project needed higher-volume event processing or cross-service integration.

### Background jobs

Some future operations may not belong directly inside a CLI command or HTTP request. Examples include route optimisation, bulk imports, report generation, scheduled reconciliation, or delayed notification processing.

A lightweight PostgreSQL-backed job table could support this before introducing external queue infrastructure.

### Fleet overview and reporting

The first read-focused operational projection is implemented: `FleetOverviewQueryPort` has memory and
PostgreSQL adapters and exposes status totals, delayed work, truck availability, route progress, segment
load, and truck utilization through CLI and HTTP.

Future reporting can build on this boundary with historical trends, SLA summaries, depot-level grouping,
throughput metrics, or a visual dashboard. Materialized views, caching, or live WebSocket updates would
only be useful if those projections became expensive or needed near-real-time browser updates.

### Advanced logistics features

Once the core backend, persistence, and query layers are stable, FleetFlow could support more advanced logistics behavior, such as route optimisation, delay prediction, SLA monitoring, customer notifications, driver/depot management, proof-of-delivery records, real-time tracking, and richer reporting.

## License

MIT
