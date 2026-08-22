"""Tests for complete command- and query-bus composition."""

import unittest
from typing import cast
from unittest.mock import MagicMock, patch

import src.composition.message_buses as subject
from src.composition.command_catalog import PUBLISHED_COMMAND_TYPES
from src.composition.query_catalog import PUBLISHED_QUERY_TYPES


class MessageBusCompositionShould(unittest.TestCase):
    """Verify every canonical message is bound to its intended workflow."""

    def setUp(self) -> None:
        """Create isolated use-case registries for registration assertions."""
        self.auth_cases = subject.AuthUseCases(
            login=MagicMock(),
            logout=MagicMock(),
            who_am_i=MagicMock(),
            register_user=MagicMock(),
            change_password=MagicMock(),
            reset_password=MagicMock(),
        )
        self.customer_cases = subject.CustomerUseCases(view_all=MagicMock())
        self.fleet_cases = subject.FleetUseCases(get_overview=MagicMock())
        self.package_cases = subject.PackageUseCases(
            create=MagicMock(),
            view=MagicMock(),
            view_all=MagicMock(),
            remove=MagicMock(),
            view_unassigned=MagicMock(),
        )
        self.route_cases = subject.RouteUseCases(
            create=MagicMock(),
            view=MagicMock(),
            view_all=MagicMock(),
            view_in_progress=MagicMock(),
            remove=MagicMock(),
            assign_packages=MagicMock(),
            assign_truck=MagicMock(),
            find_suitable_trucks=MagicMock(),
            find_suitable_routes=MagicMock(),
        )
        self.truck_cases = subject.TruckUseCases(view_all=MagicMock())
        self.state_cases = subject.StateUseCases(
            advance=MagicMock(),
            save=MagicMock(),
            load=MagicMock(),
        )
        self.audit_cases = subject.AuditUseCases(view_audit_logs=MagicMock())
        self.event_collector = MagicMock(spec=subject.EventCollector)

    def test_registers_every_command_with_expected_handler_and_use_case(self) -> None:
        """Bind every command key to the correct handler and workflow."""
        bus = MagicMock()
        expected: tuple[tuple[object, type[object], object], ...] = (
            (subject.LOGIN, subject.EventDrainingExecutor, self.auth_cases.login),
            (subject.LOGOUT, subject.EventDrainingExecutor, self.auth_cases.logout),
            (subject.REGISTER_USER, subject.EventDrainingExecutor, self.auth_cases.register_user),
            (
                subject.CHANGE_OWN_PASSWORD,
                subject.EventDrainingExecutor,
                self.auth_cases.change_password,
            ),
            (
                subject.RESET_USER_PASSWORD,
                subject.EventDrainingExecutor,
                self.auth_cases.reset_password,
            ),
            (subject.CREATE_PACKAGE, subject.EventDrainingExecutor, self.package_cases.create),
            (subject.REMOVE_PACKAGE, subject.EventDrainingExecutor, self.package_cases.remove),
            (subject.CREATE_ROUTE, subject.CreateRouteCommandHandler, self.route_cases.create),
            (subject.REMOVE_ROUTE, subject.RemoveRouteCommandHandler, self.route_cases.remove),
            (
                subject.ASSIGN_PACKAGES_TO_ROUTE,
                subject.AssignPackagesToRouteCommandHandler,
                self.route_cases.assign_packages,
            ),
            (
                subject.ASSIGN_TRUCK_TO_ROUTE,
                subject.AssignTruckToRouteCommandHandler,
                self.route_cases.assign_truck,
            ),
            (subject.LOAD_WORLD, subject.LoadWorldCommandHandler, self.state_cases.load),
            (subject.SAVE_WORLD, subject.SaveWorldCommandHandler, self.state_cases.save),
        )

        with patch.object(subject, "InProcessCommandBus", return_value=bus):
            result = subject.build_command_bus(
                self.auth_cases,
                self.package_cases,
                self.route_cases,
                self.state_cases,
                self.event_collector,
            )

        self.assertIs(result, bus)
        self.assertEqual(bus.register.call_count, len(expected))
        for actual, (key, handler_type, use_case) in zip(bus.register.call_args_list, expected, strict=True):
            actual_key, handler = cast(tuple[object, object], actual.args)
            self.assertIs(actual_key, key)
            self.assertIs(type(handler), handler_type)
            if isinstance(handler, subject.EventDrainingExecutor):
                self.assertIs(cast(object, vars(handler)["_delegate"]), use_case)
                self.assertIs(
                    cast(object, vars(handler)["_event_collector"]),
                    self.event_collector,
                )
            else:
                self.assertIs(cast(object, vars(handler)["_use_case"]), use_case)

        self.assertEqual(
            tuple(key.command_type for key, _, _ in expected),
            PUBLISHED_COMMAND_TYPES,
        )

    def test_registers_every_query_with_expected_handler_and_use_case(self) -> None:
        """Bind every query key to the correct handler and workflow."""
        bus = MagicMock()
        expected: tuple[tuple[object, type[object] | None, object], ...] = (
            (subject.VIEW_AUDITS, subject.EventDrainingExecutor, self.audit_cases.view_audit_logs),
            (subject.WHO_AM_I, None, self.auth_cases.who_am_i),
            (
                subject.VIEW_ALL_CUSTOMERS,
                subject.EventDrainingExecutor,
                self.customer_cases.view_all,
            ),
            (
                subject.GET_FLEET_OVERVIEW,
                subject.EventDrainingExecutor,
                self.fleet_cases.get_overview,
            ),
            (
                subject.VIEW_ALL_PACKAGES,
                subject.EventDrainingExecutor,
                self.package_cases.view_all,
            ),
            (subject.VIEW_PACKAGE, subject.EventDrainingExecutor, self.package_cases.view),
            (
                subject.VIEW_UNASSIGNED_PACKAGES,
                subject.ViewUnassignedPackagesQueryHandler,
                self.package_cases.view_unassigned,
            ),
            (subject.VIEW_ALL_ROUTES, subject.ViewAllRoutesQueryHandler, self.route_cases.view_all),
            (subject.VIEW_ROUTE, subject.ViewRouteQueryHandler, self.route_cases.view),
            (
                subject.VIEW_ROUTES_IN_PROGRESS,
                subject.ViewRoutesInProgressQueryHandler,
                self.route_cases.view_in_progress,
            ),
            (
                subject.FIND_SUITABLE_TRUCKS_FOR_ROUTE,
                subject.FindSuitableTrucksForRouteQueryHandler,
                self.route_cases.find_suitable_trucks,
            ),
            (
                subject.FIND_SUITABLE_ROUTES_FOR_PACKAGE,
                subject.FindSuitableRoutesForPackageQueryHandler,
                self.route_cases.find_suitable_routes,
            ),
            (subject.VIEW_ALL_TRUCKS, subject.ViewAllTrucksQueryHandler, self.truck_cases.view_all),
        )

        with patch.object(subject, "InProcessQueryBus", return_value=bus):
            result = subject.build_query_bus(
                self.audit_cases,
                self.auth_cases,
                self.customer_cases,
                self.fleet_cases,
                self.package_cases,
                self.route_cases,
                self.truck_cases,
                self.event_collector,
            )

        self.assertIs(result, bus)
        self.assertEqual(bus.register.call_count, len(expected))
        for actual, (key, handler_type, use_case) in zip(bus.register.call_args_list, expected, strict=True):
            actual_key, executor = cast(tuple[object, object], actual.args)
            self.assertIs(actual_key, key)
            if handler_type is None:
                self.assertIs(executor, use_case)
            elif handler_type is subject.EventDrainingExecutor:
                self.assertIs(type(executor), handler_type)
                self.assertIs(cast(object, vars(executor)["_delegate"]), use_case)
                self.assertIs(vars(executor)["_event_collector"], self.event_collector)
            else:
                self.assertIs(type(executor), handler_type)
                self.assertIs(cast(object, vars(executor)["_use_case"]), use_case)

        self.assertEqual(
            tuple(key.query_type for key, _, _ in expected),
            PUBLISHED_QUERY_TYPES,
        )

    def test_command_catalog_contains_unique_types(self) -> None:
        """Reject duplicate command classes in the completeness catalog."""
        self.assertEqual(len(PUBLISHED_COMMAND_TYPES), len(set(PUBLISHED_COMMAND_TYPES)))

    def test_query_catalog_contains_unique_types(self) -> None:
        """Reject duplicate query classes in the completeness catalog."""
        self.assertEqual(len(PUBLISHED_QUERY_TYPES), len(set(PUBLISHED_QUERY_TYPES)))


if __name__ == "__main__":
    unittest.main()
