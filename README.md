# FleetFlow

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Interface](https://img.shields.io/badge/Interface-CLI-0F766E)
![Architecture](https://img.shields.io/badge/Architecture-Hexagonal%20Refactor%20In%20Progress-8B5CF6)
![Tests](https://img.shields.io/badge/Tests-unittest-2563EB)

FleetFlow is a console-based logistics management app for packages, routes, trucks, customers, and user accounts across Australian hub locations. The repository has already been reorganized into a `src`-based architecture, but the running product is still a CLI application rather than an HTTP API.

## What Exists Today

- Interactive CLI menus with a command mode for power users
- Package creation, lookup, removal, and route assignment
- Route creation, lookup, removal, truck assignment, and in-progress tracking
- Truck suitability checks based on location, range, and capacity
- Customer records derived from package creation
- User authentication with employee and manager roles
- Manual save/load plus automatic state persistence after mutating commands
- JSON-backed local persistence for users and application state
- A large `unittest` suite covering domain, CLI commands, auth, and persistence

## Current Architecture

The codebase is partway through a hexagonal/backend-oriented refactor. Some folders are fully in use today, while others are scaffolding for future work.

```text
FleetFlow/
|-- data/                         # persisted JSON files such as state and users
|-- images/                       # repo assets
|-- src/
|   |-- adapters/
|   |   |-- driven/
|   |   |   |-- persistence/json/ # JSON file persistence
|   |   |   `-- security/         # password hashing
|   |   `-- driving/
|   |       |-- cli/              # menus, command factory, CLI commands
|   |       `-- http/             # placeholder for future HTTP layer
|   |-- application/
|   |   |-- services/             # auth and authorization services
|   |   |-- dto/                  # placeholder
|   |   |-- results/              # placeholder
|   |   `-- use_cases/            # placeholder
|   |-- composition/              # composition root placeholder
|   |-- core/                     # current application orchestration/state
|   |-- domain/
|   |   |-- entities/             # packages, routes, trucks, users, customers
|   |   |-- enums/
|   |   |-- services/             # map and vehicle manager
|   |   `-- value_objects/
|   `-- ports/                    # placeholder ports
|-- tests/
|-- main.py
`-- pyproject.toml
```

In practice, the current runtime flow is:

```text
CLI Menu / Command Mode
  -> CLI Command
  -> ApplicationData + Auth Services
  -> Domain Entities / Services
  -> JSON Persistence in data/
```

## Domain Snapshot

FleetFlow currently models:

- `DeliveryPackage`
- `DeliveryRoute`
- `Truck`
- `Customer`
- `User`, `Employee`, and `Manager`
- `ContactInfo`
- `Map` distance data for the supported hub codes: `SYD`, `MEL`, `ADL`, `ASP`, `BRI`, `DAR`, `PER`

## Running The App

### Prerequisites

- Python 3.13

### Environment note

The repository is not packaged yet, and current imports expect `src` to be on `PYTHONPATH`.

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python main.py
```

macOS / Linux:

```bash
export PYTHONPATH=src
python main.py
```

If you want a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
python main.py
```

There is currently no `requirements.txt`; the app itself uses the Python standard library at runtime.

## Default Login

On startup, FleetFlow bootstraps a manager account if one does not already exist:

- Username: `admin`
- Password: `ChangeMe123!`

You can then log in from the menu or command mode and change the password.

## CLI Surface

### Menu-driven flows

The main menu currently exposes:

- Packages
- Routes
- Trucks
- State
- Login, logout, who-am-I, registration, and password change
- Command mode via `cmd`

### Command mode

The command registry currently supports these commands:

- `createpackage`
- `removepackage`
- `assignpackagetoroute`
- `findsuitableroutesforpackage`
- `viewpackage`
- `viewallpackages`
- `viewunassignedpackages`
- `createroute`
- `removeroute`
- `viewroute`
- `viewallroutes`
- `assigntrucktoroute`
- `findsuitabletrucksforroute`
- `viewroutesinprogress`
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
assignpackagetoroute 1 4 5 6
assigntrucktoroute 1001 1
findsuitableroutesforpackage 4
findsuitabletrucksforroute 1
viewroute 1
viewallcustomers
save state.json
load state.json
```

## Persistence

FleetFlow stores JSON files under `data/`.

- `data/users.json`: user store
- `data/state.json`: default application state autosave target

Notes:

- Mutating commands trigger an autosave to `data/state.json`
- Manual `save` and `load` accept either bare filenames or paths
- Bare filenames are resolved into `data/`

## Authorization

Two roles exist today:

- `EMPLOYEE`
- `MANAGER`

Managers have full access. Employees can create and work with routes/packages but do not have full administrative visibility and state-management access.

## Testing

The test files use the `*_test.py` naming convention, so plain `python -m unittest discover` will not find them.

Use:

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "*_test.py"
```

macOS / Linux:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "*_test.py"
```

## Tooling

Static analysis configuration lives in `pyproject.toml` for:

- Ruff
- Pyright
- Mypy

## Development Notes

- The current product is still the CLI application in `src/adapters/driving/cli/`
- The repository structure is ahead of the runtime architecture: folders such as `ports/`, `application/use_cases/`, `application/dto/`, `application/results/`, `composition/`, and `adapters/driving/http/` exist as refactor scaffolding
- `src/core/application_data.py` is still the main orchestration point for business operations, state management, and persistence coordination
- Persistence is currently JSON-based and local-first, with autosave and explicit save/load commands
- Authentication and authorization are already split into application services, which is a good foundation for moving the same rules behind an API later
- The project is not packaged yet, so both runtime and tests currently rely on `PYTHONPATH=src`
- The automated test suite provides a solid safety net for continuing the refactor

## Status

This repository is in an active transition:

- The CLI app is the working product today
- The `src` layout already reflects a more layered architecture
- Several directories such as `application/use_cases`, `ports`, `composition`, and `adapters/driving/http` are present as scaffolding for future expansion

## Roadmap

- Move the current CLI-centered orchestration out of `src/core/application_data.py` into clearer application use cases and ports
- Add a real HTTP entry point under `src/adapters/driving/http/`
- Replace or complement JSON persistence with database-backed repositories
- Preserve the existing domain model while exposing workflows through backend services instead of CLI-only commands
- Improve packaging/import ergonomics so the project can run and test without manually setting `PYTHONPATH`
- Continue filling in the placeholder layers that already exist in `src/application/`, `src/ports/`, and `src/composition/`

## License

MIT
