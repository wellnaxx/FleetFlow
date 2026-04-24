import logging
import shlex
from datetime import datetime

from src.adapters.driving.cli.command_factory import CommandFactory
from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.state.advance_world_state import AdvanceWorldStateUseCase
from src.application.use_cases.state.save_world import SaveWorldStateUseCase

logger = logging.getLogger(__name__)


class Engine:
    """Drive the interactive CLI menus and raw command mode."""

    def __init__(
        self,
        factory: CommandFactory,
        auth: AuthService,
        authz: AuthorizationService,
        save_world_state: SaveWorldStateUseCase,
        autosave_path: str,
        advance_world_state: AdvanceWorldStateUseCase,
    ) -> None:
        """Initialize the CLI engine.

        Args:
            factory: Command factory used to parse and instantiate commands.
            auth: Authentication service used to keep menu state in sync.
            authz: Authorization service used by commands.
            save_world_state: Use case used for post-mutation autosave.
            autosave_path: Default autosave path for state mutations.
            advance_world_state: Use case used to run the pre-command heartbeat.
        """
        self._factory = factory
        self.auth = auth
        self.authz = authz
        self._save_world_state = save_world_state
        self._autosave_path = autosave_path
        self._advance_world_state = advance_world_state
        self._running: bool = False

    def _rebind_app(self) -> None:
        """Synchronize authorization state after session-changing commands."""
        self.authz.current_user = self.auth.current_user

    def start(self) -> None:
        """Main entry: shows main menu and dispatches to sub-menus or command mode."""
        self._running = True
        try:
            while self._running:
                self._print_main_menu()
                choice = input("> ").strip()
                if choice == "0":
                    print("Goodbye!")
                    break
                if choice == "1":
                    self._menu_packages()
                elif choice == "2":
                    self._menu_routes()
                elif choice == "3":
                    self._menu_trucks()
                elif choice == "4":
                    self._exec_line("viewallcustomers")
                elif choice == "5":
                    self._menu_state()
                elif choice == "login":
                    self._exec_line("login")
                elif choice == "logout":
                    self._exec_line("logout")
                elif choice == "whoami":
                    self._exec_line("whoami")
                elif choice == "register":
                    self._exec_line("registeruser")
                elif choice == "passwd":
                    self._exec_line("changepassword")
                elif choice.lower() in {"cmd", "command", ":"}:
                    self._command_mode()
                else:
                    print("Invalid option. Type a number from the menu, or 'cmd' for command mode.")
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting.")
        finally:
            self._running = False

    def _menu_packages(self) -> None:
        while True:
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
            choice = input("> ").strip()

            if choice == "0":
                break
            if choice.lower() in {"cmd", "command", ":"}:
                self._command_mode()
                continue

            try:
                if choice == "1":
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

                elif choice == "2":
                    package_id = input("Package ID to remove: ").strip()
                    self._exec_line(self._join_command(["removepackage", package_id]))

                elif choice == "3":
                    route_id = input("Route ID: ").strip()
                    pkg_ids = input("Package IDs (space-separated): ").strip()
                    # One command handles 1..N packages
                    self._exec_line(self._join_command(["assignpackagestoroute", route_id, *pkg_ids.split()]))

                elif choice == "4":
                    pid = input("Package ID to find suitable routes: ").strip()
                    self._exec_line(self._join_command(["findsuitableroutesforpackage", pid]))

                elif choice == "5":
                    pid = input("Package ID to view information about: ")
                    self._exec_line(self._join_command(["viewpackage", pid.strip()]))

                elif choice == "6":
                    self._exec_line("viewallpackages")

                elif choice == "7":
                    self._exec_line("viewunassignedpackages")

                else:
                    print("Invalid option.")
            except KeyboardInterrupt:
                print("\n(back to Packages menu)")

    def _menu_routes(self) -> None:
        while True:
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
            choice = input("> ").strip()

            if choice == "0":
                break
            if choice.lower() in {"cmd", "command", ":"}:
                self._command_mode()
                continue

            try:
                if choice == "1":
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

                elif choice == "2":
                    rid = input("Route ID: ").strip()
                    self._exec_line(self._join_command(["viewroute", rid]))

                elif choice == "3":
                    rid = input("Route ID to remove: ").strip()
                    self._exec_line(self._join_command(["removeroute", rid]))

                elif choice == "4":
                    self._exec_line("viewallroutes")

                elif choice == "5":
                    truck_id = input("Truck ID: ").strip()
                    route_id = input("Route ID: ").strip()
                    self._exec_line(self._join_command(["assigntrucktoroute", truck_id, route_id]))

                elif choice == "6":
                    rid = input("Route ID: ").strip()
                    self._exec_line(self._join_command(["findsuitabletrucksforroute", rid]))

                elif choice == "7":
                    self._exec_line("viewroutesinprogress")

                else:
                    print("Invalid option.")
            except KeyboardInterrupt:
                print("\n(back to Routes menu)")

    def _menu_trucks(self) -> None:
        while True:
            print("\nLogistics App Trucks Menu")
            print("1) View All Trucks")
            print(":) Command Mode (type 'cmd')")
            print("0) Back")
            choice = input("> ").strip()

            if choice == "0":
                break
            if choice.lower() in {"cmd", "command", ":"}:
                self._command_mode()
                continue

            try:
                if choice == "1":
                    self._exec_line("viewalltrucks")
                else:
                    print("Invalid option.")
            except KeyboardInterrupt:
                print("\n(back to Trucks menu)")

    def _menu_state(self) -> None:
        """Interactive submenu for saving and loading application state files.

        Prompts for a filename (defaults to 'state.json').
        """
        while True:
            print("\nLogistics App State Menu")
            print("1. Save state")
            print("2. Load state")
            print(":) Command Mode (type 'cmd')")
            print("0. Back to main menu")

            choice = input("> ").strip()
            try:
                if choice.lower() in {"cmd", "command", ":"}:
                    self._command_mode()
                elif choice == "1":
                    path = input("Enter filename to save state: ").strip()
                    if not path:
                        print("No file name entered.")
                        continue
                    self._exec_line(self._join_command(["save", path]))
                elif choice == "2":
                    path = input("Enter filename to load state: ").strip()
                    if not path:
                        print("No file name entered.")
                        continue
                    self._exec_line(self._join_command(["load", path]))
                elif choice == "0":
                    break
                else:
                    print("Invalid choice.")
            except KeyboardInterrupt:
                print("\n(back to State menu)")

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
                if line.lower() in {"back", "exit", "quit"}:
                    print("(leaving command mode)")
                    return
                if line.lower() in {"help", "?"}:
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

        try:
            cmd = self._factory.create(line)
            heartbeat_changed = False

            if not cmd.skips_heartbeat:
                heartbeat_summary = self._advance_world_state.execute()
                heartbeat_changed = self._heartbeat_changed(heartbeat_summary)

            out = cmd.execute()
            if cmd.mutates_session:
                self._rebind_app()

            if heartbeat_changed or (cmd.mutates_state and cmd.autosaves_state):
                try:
                    self._save_world_state.execute(self._autosave_path)
                except Exception as se:
                    logger.exception("Autosave failed after executing %r", line)
                    print(f"Warning: autosave failed: {se}")

            if out:
                print(out)

        except ValueError as e:
            msg = e.args[0] if e.args else str(e)
            print(f"Error: {msg}")

        except PermissionError as e:
            msg = e.args[0] if e.args else str(e)
            print(f"Permission Error: {msg}")

        except KeyboardInterrupt:
            print("\n(cancelled)")

        except Exception as e:
            logger.exception("Unexpected CLI error while executing %r", line)
            print(f"Unexpected error: {e}")

    @staticmethod
    def _join_command(parts: list[str]) -> str:
        return " ".join(shlex.quote(part) for part in parts)

    @staticmethod
    def _heartbeat_changed(summary: HeartbeatSummary) -> bool:
        return summary.state_changed

    @staticmethod
    def _print_main_menu() -> None:
        print("\n=== Logistics App ===")
        print("1) Packages")
        print("2) Routes")
        print("3) Trucks")
        print("4) Customers")
        print("5) State")
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
