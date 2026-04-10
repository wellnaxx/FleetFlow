# FleetFlow

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Architecture](https://img.shields.io/badge/Architecture-Console%20%2B%20Domain%20Core-6A5ACD)
![Testing](https://img.shields.io/badge/Tests-unittest-blue)
![Status](https://img.shields.io/badge/Status-Refactor%20in%20Progress-orange)

FleetFlow is a logistics management system for handling delivery packages, routes, trucks, and customer records across major Australian hubs. The current codebase is implemented as a console-driven Python application with a modular domain core, authentication and authorization, route scheduling, truck assignment, and persistent application state, and it is being refactored into a larger backend-first platform.

## Overview

This project currently follows a command-driven layered structure:

- `commands/` handles interactive user actions and command execution
- `core/` contains application orchestration, auth, persistence, serialization, and shared services
- `models/` defines the core logistics domain objects

At the moment, the live application focuses on these areas:

- package creation, lookup, removal, and route assignment
- route creation, lookup, removal, scheduling, and in-progress tracking
- truck lookup and truck-to-route assignment
- customer records linked to delivery packages
- user authentication, password management, and role-based authorization
- saving and loading application state from disk

The long-term goal is to evolve this system into a backend-first logistics platform with REST APIs, real-time tracking, event-driven processing, route optimization, simulation, and analytics.

## Current Status

This repository is currently in a refactor-and-expand phase.

- live and working today: console workflows for packages, routes, trucks, customers, auth, authorization, and state persistence
- already implemented in the domain layer: route scheduling, package-to-route validation, truck capacity/range checks, route progress tracking, and autosave/load state support
- planned next: API layer, PostgreSQL persistence, real-time package tracking, event-driven notifications, route optimization, simulation, and analytics

## Current Features

- Interactive console menus and command mode
- Delivery package creation with customer contact information
- Delivery route creation with scheduled stops and computed arrival times
- Suitable-route lookup for packages based on start and destination
- Suitable-truck lookup for routes based on capacity and range
- Truck assignment to routes
- Package assignment to routes with validation
- Route progress tracking based on current time
- View flows for routes, packages, trucks, customers, and unassigned packages
- User registration, login, logout, who-am-I, and password change flows
- Role-based authorization for protected operations
- Application state save/load support with autosave behavior
- Extensive automated unit test coverage

## Tech Stack

- Python 3.13
- unittest
- Ruff
- JSON-based local persistence for application state and users

## Project Structure

```text
FleetFlow/
|-- data/               # persisted application state and local data files
|-- images/             # project assets
|-- src/
|   |-- commands/       # command handlers for console workflows
|   |-- core/           # auth, orchestration, persistence, serialization, helpers
|   `-- models/         # logistics domain models
|-- tests/              # automated unit tests
|-- main.py             # application entrypoint
`-- pyproject.toml      # tooling configuration
```

## Architecture

The application currently follows this high-level flow:

```text
Console Input
  -> Command
  -> Application/Core Services
  -> Domain Models
  -> JSON Persistence
```

Each layer has a focused responsibility:

- commands parse user input and dispatch actions
- core services coordinate business operations, authentication, authorization, and persistence
- models represent packages, routes, trucks, users, customers, and map logic
- persistence stores users and application state locally

This structure is intended to be refactored into a backend-oriented flow later:

```text
HTTP Request
  -> Router
  -> Service
  -> Repository
  -> PostgreSQL
```

## Domain Model

The current system includes core domain objects for:

- delivery packages
- delivery routes
- trucks
- customers
- users, employees, and managers
- contact information
- map and route-distance logic

The application currently exposes these through the console interface, while the next phase will move them behind backend services and API endpoints.

## Getting Started

### Prerequisites

- Python 3.13+
- `pip`

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd FleetFlow
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python main.py
```

### 5. Run tests
```bash
python -m unittest discover
```

## Usage Surface

### Packages

- create package
- remove package
- assign package to route
- find suitable routes for a package
- view package details
- view all packages
- view unassigned packages

### Routes

- create route
- remove route
- view route details
- view all routes
- assign truck to route
- find suitable trucks for a route
- view routes in progress

### Trucks

- view all trucks

### Auth

- register user
- login
- logout
- view current user
- change password

### State Management

- save application state
- load application state

## Testing

Run tests with:

```bash
PYTHONPATH=. unittest
```

## Development Notes

- The current application is console-first with a strong domain core.
- The domain logic is structured to support a transition into a backend architecture.
- The existing test suite provides a safety net for refactoring.
- A key improvement is enabling unittest to run without manually setting PYTHONPATH.
- The next step is replacing the command layer with an API layer while preserving domain logic.

## Roadmap

- refactor into a FastAPI backend
- move persistence to PostgreSQL
- introduce service and repository layers
- add shipment lifecycle tracking
- add real-time tracking
- add event-driven notifications
- add route optimization
- add simulation engine
- add analytics and dashboard

## License

MIT
