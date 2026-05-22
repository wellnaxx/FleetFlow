import unittest
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import ValidationError

from src.adapters.driven.persistence.json.config import JSONConfig, set_json_config
from src.adapters.driving.http.schemas.auth import (
    ChangeOwnPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterUserRequest,
    ResetUserPasswordRequest,
    TokenResponse,
)
from src.adapters.driving.http.schemas.packages import PackageCreateRequest
from src.adapters.driving.http.schemas.routes import RouteResponse
from src.adapters.driving.http.schemas.state import WorldStatePathRequest
from src.adapters.driving.http.schemas.trucks import TruckResponse
from src.domain.enums.auth import Role
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_status import TruckStatus


class HttpSchemasShould(unittest.TestCase):
    def setUp(self) -> None:
        set_json_config(
            JSONConfig(
                state_path=Path("state.json"),
                export_dir=Path("exports"),
                user_store_path=Path("users.json"),
            )
        )

    def tearDown(self) -> None:
        set_json_config(None)

    def test_password_change_requests_hide_password_values_from_repr(self) -> None:
        request = ChangeOwnPasswordRequest(
            current_password="OldPass123!",
            new_password="NewPass123!",
        )
        reset = ResetUserPasswordRequest(new_password="ResetPass123!")

        self.assertNotIn("OldPass123!", repr(request))
        self.assertNotIn("NewPass123!", repr(request))
        self.assertNotIn("ResetPass123!", repr(reset))

    def test_auth_token_and_password_fields_hide_sensitive_values_from_repr(self) -> None:
        login = LoginRequest(username="alice", password="LoginPass123!")
        register = RegisterUserRequest.model_validate(
            {
                "username": "alice",
                "role": "employee",
                "name": "Alice",
                "password": "RegisterPass123!",
            }
        )
        refresh = RefreshRequest(refresh_token="refresh-token")
        token_response = TokenResponse(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
        )

        self.assertNotIn("LoginPass123!", repr(login))
        self.assertNotIn("RegisterPass123!", repr(register))
        self.assertNotIn("refresh-token", repr(refresh))
        self.assertNotIn("access-token", repr(token_response))
        self.assertNotIn("refresh-token", repr(token_response))

    def test_password_change_requests_reject_oversized_passwords(self) -> None:
        password = "A" * 129

        with self.assertRaises(ValidationError):
            ChangeOwnPasswordRequest(current_password=password, new_password="NewPass123!")

        with self.assertRaises(ValidationError):
            ResetUserPasswordRequest(new_password=password)

    def test_package_create_request_validates_customer_email(self) -> None:
        with self.assertRaises(ValidationError):
            PackageCreateRequest(
                start_location="SYD",
                end_location="MEL",
                weight=1.0,
                customer_name="Alice",
                customer_email="not-an-email",
            )

    def test_register_user_request_validates_email(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterUserRequest.model_validate(
                {
                    "username": "alice",
                    "role": Role.EMPLOYEE,
                    "name": "Alice",
                    "email": "not-an-email",
                    "password": "Pass1234!",
                }
            )

    def test_route_response_uses_domain_route_status_values(self) -> None:
        route = RouteResponse(
            route_id=1,
            locations=["SYD", "MEL"],
            departure_time=None,
            status=RouteStatus.PLANNED,
            truck_id=None,
            total_distance_km=1,
            eta_final=None,
            package_ids=[],
        )

        self.assertIs(route.status, RouteStatus.PLANNED)

    def test_truck_response_validates_status_and_busy_window(self) -> None:
        busy_from = datetime.now()
        truck = TruckResponse(
            vehicle_id=1001,
            name="Scania",
            capacity=1,
            max_range=1,
            status=TruckStatus.FREE,
            current_location=None,
            route_id=None,
            busy_from=busy_from,
            busy_until=busy_from + timedelta(hours=1),
            in_transit_to=None,
        )

        self.assertIs(truck.status, TruckStatus.FREE)

        with self.assertRaises(ValidationError):
            TruckResponse.model_validate(
                {
                    "vehicle_id": 1001,
                    "name": "Scania",
                    "capacity": 1,
                    "max_range": 1,
                    "status": "maintenance",
                    "current_location": None,
                    "route_id": None,
                    "busy_from": None,
                    "busy_until": None,
                    "in_transit_to": None,
                }
            )

        with self.assertRaises(ValidationError):
            TruckResponse(
                vehicle_id=1001,
                name="Scania",
                capacity=1,
                max_range=1,
                status=TruckStatus.ON_THE_WAY,
                current_location=None,
                route_id=None,
                busy_from=busy_from,
                busy_until=busy_from - timedelta(hours=1),
                in_transit_to=None,
            )

    def test_world_state_path_request_resolves_safe_export_paths(self) -> None:
        request = WorldStatePathRequest(path="daily/state.json")

        resolved = Path(request.path)
        self.assertTrue(resolved.is_absolute())
        self.assertEqual(resolved.name, "state.json")
        self.assertEqual(resolved.parent.name, "daily")

    def test_world_state_path_request_rejects_traversal_and_absolute_paths(self) -> None:
        with self.assertRaises(ValidationError):
            WorldStatePathRequest(path="../state.json")

        with self.assertRaises(ValidationError):
            WorldStatePathRequest(path="/tmp/state.json")
