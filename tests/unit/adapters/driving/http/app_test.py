"""Tests for FastAPI application-level router registration."""

import unittest

from fastapi.routing import APIRoute

from src.adapters.driving.http.app import app


class HTTPAppShould(unittest.TestCase):
    """Verify feature routers remain exposed by the configured application."""

    def test_registers_fleet_overview_endpoint(self) -> None:
        """Expose the fleet overview through the versioned API prefix."""
        matching_routes = [
            route
            for route in app.routes
            if isinstance(route, APIRoute) and route.path == "/api/fleet/overview"
        ]

        self.assertEqual(len(matching_routes), 1)
        self.assertIn("GET", matching_routes[0].methods)
