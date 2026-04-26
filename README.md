# FleetFlow

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/Interface-CLI-0F766E)
![Architecture](https://img.shields.io/badge/Architecture-Hexagonal--style%20CLI-8B5CF6)
![Tests](https://img.shields.io/badge/Tests-pytest%20%2B%20unittest-2563EB)

FleetFlow is a console-based logistics management system for packages, delivery routes, trucks, customers, and authenticated users across Australian freight hub locations. The active user interface is a CLI, but the internals are structured around domain entities, application use cases, services, ports, adapters, and a composition root so the same workflows can be reused by future driving adapters such as an HTTP API.

## Capabilities

FleetFlow currently supports:

- Interactive menu-driven operation and command-mode workflows.
- Package creation, lookup, removal, unassigned-package listing, and route assignment.
- Route creation, lookup, removal, in-progress tracking, package assignment, and truck assignment.
- Truck fleet management with deterministic city dispersion.
- Truck suitability checks for start-location compatibility, route range, time-window availability, and carrying capacity.
- Segment-based capacity validation, so a truck is checked against the maximum load carried on each route leg rather than total package weight across the whole route.
- Customer records derived from package creation, including email and phone lookup indexes.
- User authentication with manager and employee roles.
- Role-based authorization around CLI commands and application use cases.
- Password hashing with PBKDF2-HMAC and strict persisted password-hash validation.
- Manual save/load plus autosave after mutating commands when autosave is enabled.
- Versioned JSON world-state snapshots containing customers, packages, routes, repository counters, and truck runtime state.
- Startup recovery for default saved state: missing state is ignored, corrupt state is quarantined, and unexpected runtime errors still fail loudly.
- A large automated test suite covering domain behavior, application services, use cases, CLI commands, persistence, runtime swaps, and startup behavior.

## Architecture Overview

FleetFlow uses a hexagonal-style layered architecture. The CLI is the current driving adapter. JSON persistence, in-memory repositories, security, and runtime state management are driven adapters behind application-level ports and services.

```text
FleetFlow/
|-- data/                         # local runtime JSON files; generated, not source fixtures
|-- images/                       # project images/assets
|-- src/
|   |-- adapters/
|   |   |-- driven/
|   |   |   |-- persistence/json/ # JSON world-state and user persistence
|   |   |   |-- persistence/memory/# in-memory repositories and runtime state gateway
|   |   |   `-- security/         # password hashing
|   |   `-- driving/
|   |       |-- cli/              # engine, menus, command factory, CLI commands
|   |       `-- http/             # placeholder for a future HTTP adapter
|   |-- application/
|   |   |-- config/               # application-level configuration constants
|   |   |-- dto/                  # persisted snapshot and runtime transfer objects
|   |   |-- exceptions/           # application and world-state exception hierarchy
|   |   |-- models/               # persisted application models such as UserRecord
|   |   |-- results/              # use-case/service result objects
|   |   |-- services/             # auth, authorization, heartbeat, reconciliation, snapshot services
|   |   `-- use_cases/            # auth, package, route, truck, customer, and state workflows
|   |-- composition/              # dependency container / composition root
|   |-- domain/
|   |   |-- entities/             # customers, packages, routes, trucks, users
|   |   |-- enums/                # roles, permissions, item/route/truck statuses
|   |   |-- services/             # Map and VehicleManager domain services
|   |   `-- value_objects/        # ContactInfo, LocationCode
|   `-- ports/
|       |-- input/                # reserved for future input-port abstractions
|       `-- output/               # repository, persistence, runtime, and vehicle ports
|-- tests/
|-- main.py
`-- pyproject.toml
```

The runtime flow is:

```text
CLI Menu / Command Mode
  -> CLI Command
  -> Application Use Case
  -> Application Service / Port
  -> Domain Entity / Domain Service
  -> In-memory Repository or JSON Persistence Adapter
```

The composition root is `src/composition/container.py`. It wires repositories, domain services, application services, world-state persistence, runtime state management, and all CLI-facing use cases.

## Domain Model

FleetFlow models:

- `Customer`
- `DeliveryPackage`
- `DeliveryRoute`
- `Truck`
- `User`, `Employee`, and `Manager`
- `ContactInfo`
- `LocationCode`
- `Map`
- `VehicleManager`

Supported hub codes are:

```text
SYD, MEL, ADL, ASP, BRI, DAR, PER
```

`LocationCode` normalizes location text to uppercase. `Map` owns the supported location set and intercity distances.

## Route, Truck, and Package Rules

FleetFlow enforces the main logistics invariants in the domain and application layers:

- Routes must contain at least two unique supported locations.
- Packages can only be assigned to routes that contain their start and end locations in the correct order.
- Scheduled routes compute stop arrival times and final ETA from map distances and route speed.
- Package assignment updates package-route links and expected arrival when possible.
- Removing a package from a route clears its active assignment state.
- Truck assignment checks current location, route range, availability window, and carrying capacity.
- Carrying capacity is checked by maximum segment load rather than total assigned package weight.
- Heartbeat/reconciliation updates route statuses, truck positions, truck releases, package statuses, package current locations, and expected arrivals.

## World-State Persistence

FleetFlow stores local JSON files under `data/` by default:

- `data/users.json`: persisted user records and password hashes.
- `data/state.json`: default world-state autosave target.

World-state saves are versioned snapshots. The current canonical schema version is `2` and includes:

- repository id counters,
- customers,
- packages,
- routes,
- truck runtime snapshots.

The state pipeline is:

```text
Save:
Runtime repositories + truck fleet
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

At startup, FleetFlow attempts to load the default state file. Missing default state is treated as a no-op. Corrupt world-state JSON is quarantined with a `.corrupt.<timestamp>` suffix and the application starts with empty runtime state. Non-corruption runtime errors are not swallowed.

## Authentication and Authorization

FleetFlow has two roles:

- `MANAGER`
- `EMPLOYEE`

Managers have full access. Employees can perform day-to-day logistics operations but do not have unrestricted administrative/state-management access.

On first startup, if no `admin` user exists, FleetFlow creates the initial manager interactively. It prompts for a password and confirmation:

```text
Create initial manager password:
Confirm initial manager password:
```

There is no hardcoded default admin password in the current version.

If the application is started non-interactively and no admin user exists, startup fails with a clear error telling you to run it interactively once.

## Running the App

### Prerequisite

- Python 3.13

The runtime application uses the Python standard library. No runtime `requirements.txt` is currently needed.

### Windows PowerShell

```powershell
python main.py
```

### macOS / Linux

```bash
python main.py
```

If imports fail in your environment, run from the repository root and set `PYTHONPATH` explicitly:

```powershell
$env:PYTHONPATH = "."
python main.py
```

```bash
PYTHONPATH=. python main.py
```

### Optional virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python main.py
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python main.py
```

## CLI Surface

### Menu-driven flows

The main menu exposes:

- Packages
- Routes
- Trucks
- Customers
- State
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
save state.json
load state.json
login admin
whoami
changepassword admin
logout
```

Quoted arguments are supported in command mode through shell-style parsing, so names with spaces should be quoted.

## Autosave and Heartbeat

The CLI engine performs heartbeat/reconciliation around command execution. Reconciliation may update route status, truck position, truck release state, package status, package current location, and expected arrival.

Mutating commands are autosaved to the default world-state path when autosave is enabled. Some commands intentionally mutate runtime state without immediately autosaving over the current file, such as `load`.

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

## Tooling


Static-analysis and formatting/lint configuration live in `pyproject.toml`.

Configured tools:

- Ruff
- Pyright
- Mypy
- Pytest

These are development tools and are not required to run the CLI application.
Example commands, assuming the tools are installed:

```bash
python -m ruff check .
python -m pyright
python -m mypy .
```

## Roadmap

FleetFlow is currently a CLI-first logistics backend with a layered/hexagonal architecture, domain entities, use cases, ports, in-memory repositories, JSON world-state persistence, authentication, autosave/load support, heartbeat reconciliation, and segment-aware route capacity checks.

The current architecture leaves several possible paths for future development. These are not required for the core project to work, but they are natural extensions if the project continues growing.

### Backend hardening

The existing backend can be tightened further by cleaning up `LocationCode` boundary ergonomics, making world-state schema compatibility rules more explicit, strengthening truck snapshot invariant validation, removing generated/private files from exported archives, and keeping documentation aligned with the actual codebase.

### Command bus layer

FleetFlow already uses application use cases as the main operation boundary. A future command bus could make that boundary more formal by giving CLI commands, future API requests, authorization checks, logging, autosave behavior, and metrics one consistent dispatch path.

This would allow the current use cases to act as command handlers without rewriting the domain model.

### HTTP API adapter

Because the application layer is already separated from the CLI, a REST API could be added as another driving adapter. A FastAPI adapter would let external clients use the same package, route, truck, customer, authentication, save/load, and heartbeat workflows that the CLI currently uses.

The CLI could remain supported beside the API instead of being replaced by it.

### PostgreSQL persistence adapter

The current in-memory repositories and JSON world-state persistence work well for local development and testing. A PostgreSQL adapter could be added behind the existing repository ports for a more realistic long-running backend.

JSON save/load could remain useful as an import/export, backup, or local snapshot mechanism.

### Audit log and domain events

FleetFlow could record important completed actions, such as package assignment, route scheduling, truck dispatch, truck release, package delivery, login events, and world-state loads.

A simple PostgreSQL-backed `audit_log` or `domain_events` table would be enough at first. External event brokers such as Kafka or Redis Streams would only make sense later if the project needed higher-volume event processing.

### Background jobs

Some future operations may not belong directly inside a CLI command or HTTP request. Examples include route optimisation, bulk imports, report generation, scheduled reconciliation, or delayed notification processing.

A lightweight PostgreSQL-backed job table could support this before introducing external queue infrastructure.

### Dashboard and query layer

FleetFlow could add read-focused query services for operational visibility. Possible dashboard data includes fleet status, package status, route progress, delayed packages, assigned capacity, completed routes, and truck utilisation.

This can start with indexed PostgreSQL queries or materialized views. Redis caching or live WebSocket updates would only be useful if the dashboard became more dynamic or expensive to query.

### Advanced logistics features

Once the core backend, persistence, and query layers are stable, FleetFlow could support more advanced logistics behavior, such as route optimisation, delay prediction, SLA monitoring, customer notifications, driver/depot management, proof-of-delivery records, real-time tracking, and richer reporting.

## License

MIT
