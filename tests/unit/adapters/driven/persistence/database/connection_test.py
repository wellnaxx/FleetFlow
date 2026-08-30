"""Tests for PostgreSQL connection construction."""

import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.connection import get_connection

MODULE = "src.adapters.driven.persistence.database.connection"


class GetConnectionShould(unittest.TestCase):
    """Verify database sessions preserve UTC timestamp hydration."""

    @patch(f"{MODULE}.psycopg.connect")
    @patch(f"{MODULE}.get_postgres_config")
    def test_open_postgres_session_in_utc(
        self,
        get_config_mock: MagicMock,
        connect_mock: MagicMock,
    ) -> None:
        config = get_config_mock.return_value
        config.name = "fleetflow"
        config.user = "fleet"
        config.password = "secret"
        config.host = "localhost"
        config.port = 5432

        result = get_connection()

        self.assertIs(result, connect_mock.return_value)
        connect_mock.assert_called_once_with(
            dbname="fleetflow",
            user="fleet",
            password="secret",
            host="localhost",
            port=5432,
            options="-c timezone=UTC",
        )
