"""Interactive CLI engine and command execution loop."""

import logging
import shlex
from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from src.adapters.driving.cli.command_factory import CommandFactory
from src.application.commands.state.advance_world import ADVANCE_WORLD_STATE, AdvanceWorldStateCommand
from src.application.enums.event_sources import EventSource
from src.application.eventing.collector import EventCollector
from src.application.eventing.context import EventContext
from src.application.eventing.current_context import bind_event_context
from src.application.eventing.envelope import EventActor
from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.state.save_world import SaveWorldStateUseCase
from src.ports.input.command_bus import CommandBus

logger = logging.getLogger(__name__)

_COMMAND_MODE_CHOICES = frozenset({"cmd", "command", ":"})

type MenuAction = Callable[[], None]
type MenuActions = dict[str, MenuAction]


class Engine:
    """Drive the interactive CLI menus and raw command mode."""

    def __init__(
        self,
        factory: CommandFactory,
        auth: AuthService,
        authz: AuthorizationService,
        save_world_state: SaveWorldStateUseCase,
        autosave_path: str,
        command_bus: CommandBus,
        autosave_enabled: bool,
        event_collector: EventCollector,
    ) -> None:
        """Initialize the CLI engine.

        Args:
            factory: Command factory used to parse and instantiate commands.
            auth: Authentication service used to keep menu state in sync.
            authz: Authorization service used by commands.
            save_world_state: Use case used for post-mutation autosave.
            autosave_path: Default autosave path for state mutations.
            command_bus: Application command bus used to run the internal
                pre-command heartbeat.
            autosave_enabled: Whether autosave is enabled.
            event_collector: Collector used to publish events from the
                remaining directly executed autosave workflow. Heartbeat event
                publication is owned by its command-bus executor.
        """
        self._factory = factory
        self.auth = auth
        self.authz = authz
        self._save_world_state = save_world_state
        self._autosave_path = autosave_path
        self._command_bus = command_bus
        self._autosave_enabled: bool = autosave_enabled
        self._running: bool = False
        self._event_collector = event_collector

    def _rebind_app(self) -> None:
        """Synchronize authorization state after session-changing commands."""
        self.authz.current_user = self.auth.current_user

    def start(self) -> None:
        """Main entry: shows main menu and dispatches to sub-menus or command mode."""
        self._running = True

        actions = self._with_command_mode_aliases(
            {
                "0": self._exit,
                "1": self._menu_packages,
                "2": self._menu_routes,
                "3": self._menu_trucks,
                "4": lambda: self._exec_line("viewallcustomers"),
                "5": self._menu_state,
                "6": self._menu_audits,
                "7": self._get_fleet_overview,
                "login": lambda: self._exec_line("login"),
                "logout": lambda: self._exec_line("logout"),
                "whoami": lambda: self._exec_line("whoami"),
                "register": lambda: self._exec_line("registeruser"),
                "passwd": lambda: self._exec_line("changepassword"),
            },
            self._command_mode,
        )

        try:
            while self._running:
                self._print_main_menu()

                choice = input("> ").strip()
                action = actions.get(choice.lower())

                if action is None:
                    print("Invalid option. Type a number from the menu, or 'cmd' for command mode.")
                    continue

                action()
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting.")
        finally:
            self._running = False

    def _exit(self) -> None:
        """Stop the main menu loop without terminating the Python process."""
        print("Goodbye!")
        self._running = False

    def _get_fleet_overview(self) -> None:
        """Prompt for the active-route limit and display the fleet overview."""
        active_route_limit = input("Active route limit (blank for 10): ").strip()
        parts = ["getfleetoverview"]
        if active_route_limit:
            parts.append(active_route_limit)
        self._exec_line(self._join_command(parts))

    def _run_submenu(
        self,
        *,
        render: Callable[[], None],
        actions: MenuActions,
        name: str,
    ) -> None:
        """Render and dispatch one submenu until the user returns to its parent.

        Args:
            render: Function that prints the submenu options.
            actions: Normalized user choices mapped to submenu actions.
            name: Label used in cancellation feedback.
        """
        while True:
            render()
            try:
                choice = input("> ").strip().lower()
            except KeyboardInterrupt:
                print("\n(back to main menu)")
                return

            if choice == "0":
                return

            action = actions.get(choice)
            if action is None:
                print("Invalid option.")
                continue

            try:
                action()
            except KeyboardInterrupt:
                print(f"\n(cancelled {name} operation)")

    @staticmethod
    def _with_command_mode_aliases(actions: MenuActions, command_mode: MenuAction) -> MenuActions:
        """Add command-mode aliases to a menu action table."""
        return actions | dict.fromkeys(_COMMAND_MODE_CHOICES, command_mode)

    def _menu_packages(self) -> None:
        """Show package operations and dispatch the selected action."""
        self._run_submenu(
            render=self._print_packages_menu,
            actions=self._with_command_mode_aliases(
                {
                    "1": self._create_package,
                    "2": self._remove_package,
                    "3": self._assign_packages_to_route,
                    "4": self._find_suitable_routes,
                    "5": self._view_package,
                    "6": lambda: self._exec_line("viewallpackages"),
                    "7": lambda: self._exec_line("viewunassignedpackages"),
                },
                self._command_mode,
            ),
            name="Packages",
        )

    def _create_package(self) -> None:
        """Prompt for package details and execute the create command."""
        start = input("Start location: ").strip()
        end = input("End location: ").strip()
        weight = input("Weight: ").strip()
        name = input("Customer name: ").strip()
        email = input("Email (optional): ").strip()
        phone = input("Phone (optional): ").strip()

        parts = [
            "createpackage",
            start,
            end,
            weight,
            name,
        ]
        if email:
            parts.append(email)
        if phone:
            parts.append(phone)

        self._exec_line(self._join_command(parts))

    def _remove_package(self) -> None:
        """Prompt for a package identifier and execute the remove command."""
        package_id = input("Package ID to remove: ").strip()
        self._exec_line(self._join_command(["removepackage", package_id]))

    def _assign_packages_to_route(self) -> None:
        """Prompt for a route and package identifiers, then execute assignment."""
        route_id = input("Route ID: ").strip()
        pkg_ids = input("Package IDs (space-separated): ").strip()
        # One command handles 1..N packages
        self._exec_line(self._join_command(["assignpackagestoroute", route_id, *pkg_ids.split()]))

    def _find_suitable_routes(self) -> None:
        """Prompt for a package identifier and find its suitable routes."""
        pid = input("Package ID to find suitable routes: ").strip()
        self._exec_line(self._join_command(["findsuitableroutesforpackage", pid]))

    def _view_package(self) -> None:
        """Prompt for a package identifier and display its details."""
        pid = input("Package ID to view information about: ")
        self._exec_line(self._join_command(["viewpackage", pid.strip()]))

    def _menu_routes(self) -> None:
        """Show route operations and dispatch the selected action."""
        self._run_submenu(
            render=self._print_routes_menu,
            actions=self._with_command_mode_aliases(
                {
                    "1": self._create_route,
                    "2": self._view_route,
                    "3": self._remove_route,
                    "4": lambda: self._exec_line("viewallroutes"),
                    "5": self._assign_truck_to_route,
                    "6": self._find_suitable_trucks_for_route,
                    "7": lambda: self._exec_line("viewroutesinprogress"),
                },
                self._command_mode,
            ),
            name="Routes",
        )

    def _create_route(self) -> None:
        """Prompt for route locations and an optional departure time."""
        locs = input("Enter locations (space-separated, at least 2): ").strip()
        dep = input("Enter departure time (YYYY-MM-DD HH:MM) or leave blank for now: ").strip()

        if dep:
            try:
                datetime.strptime(dep, "%Y-%m-%d %H:%M")
                self._exec_line(self._join_command(["createroute", *locs.split(), dep]))
            except ValueError:
                print("Invalid date format, must be YYYY-MM-DD HH:MM")
        else:
            self._exec_line(self._join_command(["createroute", *locs.split()]))

    def _view_route(self) -> None:
        """Prompt for a route identifier and display its details."""
        rid = input("Route ID: ").strip()
        self._exec_line(self._join_command(["viewroute", rid]))

    def _remove_route(self) -> None:
        """Prompt for a route identifier and execute the remove command."""
        rid = input("Route ID to remove: ").strip()
        self._exec_line(self._join_command(["removeroute", rid]))

    def _assign_truck_to_route(self) -> None:
        """Prompt for truck and route identifiers, then execute assignment."""
        truck_id = input("Truck ID: ").strip()
        route_id = input("Route ID: ").strip()
        self._exec_line(self._join_command(["assigntrucktoroute", truck_id, route_id]))

    def _find_suitable_trucks_for_route(self) -> None:
        """Prompt for a route identifier and find suitable trucks."""
        rid = input("Route ID: ").strip()
        self._exec_line(self._join_command(["findsuitabletrucksforroute", rid]))

    def _menu_trucks(self) -> None:
        """Show truck operations and dispatch the selected action."""
        self._run_submenu(
            render=self._print_trucks_menu,
            actions=self._with_command_mode_aliases(
                {"1": lambda: self._exec_line("viewalltrucks")},
                self._command_mode,
            ),
            name="Trucks",
        )

    def _menu_state(self) -> None:
        """Show save/load operations and prompt for a required snapshot path."""
        self._run_submenu(
            render=self._print_state_menu,
            actions=self._with_command_mode_aliases(
                {"1": self._save_state, "2": self._load_state},
                self._command_mode,
            ),
            name="State",
        )

    def _save_state(self) -> None:
        """Prompt for a snapshot path and execute the save command."""
        path = input("Enter filename to save state: ").strip()
        if not path:
            print("No file name entered.")
            return
        self._exec_line(self._join_command(["save", path]))

    def _load_state(self) -> None:
        """Prompt for a snapshot path and execute the load command."""
        path = input("Enter filename to load state: ").strip()
        if not path:
            print("No file name entered.")
            return
        self._exec_line(self._join_command(["load", path]))

    def _menu_audits(self) -> None:
        """Show audit-log operations and dispatch the selected action."""
        self._run_submenu(
            render=self._print_audit_menu,
            actions=self._with_command_mode_aliases(
                {"1": self._view_audits},
                self._command_mode,
            ),
            name="Audit",
        )

    def _view_audits(self) -> None:
        """Prompt for audit-log filters and execute the audit listing command."""
        args: list[str] = []

        self._append_optional_option(args, "--event_type", "Event type")
        self._append_optional_option(args, "--resource_type", "Resource type")
        self._append_optional_option(args, "--resource_id", "Resource ID")
        self._append_optional_option(args, "--action", "Action")
        self._append_optional_option(args, "--actor_user_id", "Actor user ID")
        self._append_optional_option(args, "--actor_username", "Actor username")
        self._append_optional_option(args, "--source", "Source")
        self._append_optional_option(args, "--occurred_from", "Occurred from")
        self._append_optional_option(args, "--occurred_to", "Occurred to")
        self._append_optional_option(args, "--created_from", "Created from")
        self._append_optional_option(args, "--created_to", "Created to")

        limit = input("Limit (blank for all): ").strip()
        if limit:
            args.extend(["--limit", limit])

        offset = input("Offset (blank for 0): ").strip()
        if offset:
            args.extend(["--offset", offset])

        include_total = input("Include total? (y/N): ").strip().lower()
        if include_total in {"y", "yes"}:
            if not limit:
                print("Include total requires a limit.")
                return
            args.append("--total")

        self._exec_line(self._join_command(["viewauditlogs", *args]))

    @staticmethod
    def _append_optional_option(args: list[str], option: str, prompt: str) -> None:
        """Append a CLI option when the corresponding prompt receives a value."""
        value = input(f"{prompt} (optional): ").strip()
        if value:
            args.extend([option, value])

    def _command_mode(self) -> None:
        """
        Raw command input loop (power users).
        - Type 'back' to return to previous menu.
        - Type 'help' to list common commands.
        """
        print("\n: Command mode (type 'back' to return, 'help' for hints)")
        while True:
            try:
                line = input(": ").strip()
                if not line:
                    continue
                normalized_line = line.lower()
                if normalized_line in {"back", "exit", "quit"}:
                    print("(leaving command mode)")
                    return
                if normalized_line in {"help", "?"}:
                    self._print_help()
                    continue
                self._exec_line(line)
            except KeyboardInterrupt:
                print("\n(leaving command mode)")
                return

    def _exec_line(self, line: str) -> None:
        """
        Parse and execute a single command line.
        - Creates the command first.
        - Runs heartbeat before execution unless the command opts out.
        - Prints command output or a friendly error.
        """
        if not line or not line.strip():
            return

        with bind_event_context(
            EventContext(
                correlation_id=uuid4(),
                source=EventSource.CLI,
                actor=self._event_actor(),
            )
        ):
            self._exec_line_in_context(line)

    def _exec_line_in_context(self, line: str) -> None:
        """Execute one CLI workflow while its event context is bound.

        Args:
            line: Non-empty command line to parse and execute.
        """
        try:
            cmd = self._factory.create(line)
            heartbeat_changed = False
            command_name = type(cmd).__name__
            logger.info("Executing CLI command %s.", command_name)

            if not cmd.skips_heartbeat:
                heartbeat_summary = self._command_bus.dispatch(
                    key=ADVANCE_WORLD_STATE,
                    command=AdvanceWorldStateCommand(),
                )
                heartbeat_changed = self._heartbeat_changed(heartbeat_summary)
                if heartbeat_changed:
                    logger.info("Pre-command heartbeat changed world state before %s.", command_name)

            out = cmd.execute()
            if cmd.mutates_session:
                logger.debug("Rebinding CLI authorization state after %s.", command_name)
                self._rebind_app()

            if self._autosave_enabled and (heartbeat_changed or (cmd.mutates_state and cmd.autosaves_state)):
                try:
                    logger.info("Autosaving world state after %s.", command_name)
                    self._save_world_state.execute(self._autosave_path)
                except Exception as se:
                    try:
                        self._event_collector.drain((self._save_world_state,))
                    except Exception:
                        logger.exception("Failed to publish autosave failure events.")
                    logger.exception("Autosave failed after executing %r", line)
                    print(f"Warning: autosave failed: {se}")
                else:
                    self._event_collector.drain((self._save_world_state,))

            if out:
                print(out)
            logger.info("CLI command %s completed.", command_name)

        except ValueError as e:
            msg = e.args[0] if e.args else str(e)
            logger.debug("CLI command rejected: %s", msg)
            print(f"Error: {msg}")

        except PermissionError as e:
            msg = e.args[0] if e.args else str(e)
            logger.warning("CLI command denied: %s", msg)
            print(f"Permission Error: {msg}")

        except KeyboardInterrupt:
            print("\n(cancelled)")

        except Exception as e:
            logger.exception("Unexpected CLI error while executing %r", line)
            print(f"Unexpected error: {e}")

    def _event_actor(self) -> EventActor | None:
        """Return the authenticated CLI actor captured before command execution.

        Login and registration commands intentionally run without an actor when
        no session exists yet. Session-mutating commands retain the actor that
        initiated the workflow because the context is created before execution.
        """
        user = self.auth.current_user
        if user is None:
            return None

        username = user.username

        return EventActor(
            user_id=user.user_id,
            username=username,
        )

    @staticmethod
    def _join_command(parts: list[str]) -> str:
        return " ".join(shlex.quote(part) for part in parts)

    @staticmethod
    def _heartbeat_changed(summary: HeartbeatSummary) -> bool:
        return summary.state_changed

    @staticmethod
    def _print_packages_menu() -> None:
        """Print package submenu options."""
        print("\nLogistics App Packages Menu")
        print("1) Create Package")
        print("2) Remove Package")
        print("3) Assign Package(s) to Route")
        print("4) Choose Route For Package (search suitable)")
        print("5) View Package Information")
        print("6) View All Packages")
        print("7) View Unassigned Packages")
        print(":) Command Mode (type 'cmd')")
        print("0) Back")

    @staticmethod
    def _print_routes_menu() -> None:
        """Print route submenu options."""
        print("\nLogistics App Routes Menu")
        print("1) Create Route")
        print("2) View Route Information")
        print("3) Remove Route")
        print("4) View All Routes")
        print("5) Assign Truck to Route")
        print("6) Find Suitable Trucks for Route")
        print("7) View Routes In Progress")
        print(":) Command Mode (type 'cmd')")
        print("0) Back")

    @staticmethod
    def _print_trucks_menu() -> None:
        """Print truck submenu options."""
        print("\nLogistics App Trucks Menu")
        print("1) View All Trucks")
        print(":) Command Mode (type 'cmd')")
        print("0) Back")

    @staticmethod
    def _print_state_menu() -> None:
        """Print world-state submenu options."""
        print("\nLogistics App State Menu")
        print("1) Save state")
        print("2) Load state")
        print(":) Command Mode (type 'cmd')")
        print("0) Back to main menu")

    @staticmethod
    def _print_audit_menu() -> None:
        """Print audit submenu options."""
        print("\nLogistics App Audit Menu")
        print("1) View Audit Logs")
        print(":) Command Mode (type 'cmd')")
        print("0) Back to main menu")

    @staticmethod
    def _print_main_menu() -> None:
        print("\n=== Logistics App ===")
        print("1) Packages")
        print("2) Routes")
        print("3) Trucks")
        print("4) Customers")
        print("5) State")
        print("6) Audit Logs")
        print("7) Fleet Overview")
        print("cmd) Command Mode")
        print("login) Login")
        print("logout) Logout")
        print("whoami) Who am I")
        print("register) Register User")
        print("passwd) Change Password")
        print("0) Exit")

    @staticmethod
    def _print_help() -> None:
        print("Common commands:")
        print('  createpackage SYD MEL 10 John "" 0412345678')
        print("  createroute SYD MEL 2025-09-12 06:00")
        print("  assignpackagestoroute <route_id> <pkg1> [pkg2] ...")
        print("  assigntrucktoroute <truck_id> <route_id>")
        print("  viewroute <route_id>")
        print("  viewallroutes")
        print("  viewallpackages")
        print("  viewalltrucks")
        print("  viewauditlogs --limit 50 --total")
        print("  getfleetoverview [active_route_limit]")
        print("  save <filename>")
        print("  load <filename>")
        print("  login | logout | whoami")
