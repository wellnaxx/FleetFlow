import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.unit_of_work import PostgresUnitOfWork

MODULE = "src.adapters.driven.persistence.database.unit_of_work"


class PostgresUnitOfWork_Should(unittest.TestCase):
    @patch(f"{MODULE}.PostgresTruckUnitOfWorkRepository")
    @patch(f"{MODULE}.PostgresPackageUnitOfWorkRepository")
    @patch(f"{MODULE}.PostgresRouteUnitOfWorkRepository")
    @patch(f"{MODULE}.get_connection")
    def test_enter_opens_connection_and_exposes_transaction_bound_repositories(
        self,
        get_connection_mock: MagicMock,
        route_repo_cls: MagicMock,
        package_repo_cls: MagicMock,
        truck_repo_cls: MagicMock,
    ) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn

        unit_of_work = PostgresUnitOfWork()

        active = unit_of_work.__enter__()

        self.assertIs(active, unit_of_work)
        get_connection_mock.assert_called_once_with()
        conn.cursor.assert_called_once_with()
        route_repo_cls.assert_called_once_with(cursor)
        package_repo_cls.assert_called_once_with(cursor)
        truck_repo_cls.assert_called_once_with(cursor)
        self.assertIs(unit_of_work.routes, route_repo_cls.return_value)
        self.assertIs(unit_of_work.packages, package_repo_cls.return_value)
        self.assertIs(unit_of_work.trucks, truck_repo_cls.return_value)

    @patch(f"{MODULE}.get_connection")
    def test_enter_closes_connection_when_cursor_creation_fails(self, get_connection_mock: MagicMock) -> None:
        conn = MagicMock()
        conn.cursor.side_effect = RuntimeError("cursor failed")
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()

        with self.assertRaises(RuntimeError):
            unit_of_work.__enter__()

        conn.close.assert_called_once_with()

    @patch(f"{MODULE}.PostgresTruckUnitOfWorkRepository")
    @patch(f"{MODULE}.PostgresPackageUnitOfWorkRepository")
    @patch(f"{MODULE}.PostgresRouteUnitOfWorkRepository", side_effect=RuntimeError("repo failed"))
    @patch(f"{MODULE}.get_connection")
    def test_enter_closes_cursor_and_connection_when_repository_creation_fails(
        self,
        get_connection_mock: MagicMock,
        route_repo_cls: MagicMock,
        package_repo_cls: MagicMock,
        truck_repo_cls: MagicMock,
    ) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()

        with self.assertRaises(RuntimeError):
            unit_of_work.__enter__()

        route_repo_cls.assert_called_once_with(cursor)
        package_repo_cls.assert_not_called()
        truck_repo_cls.assert_not_called()
        cursor.close.assert_called_once_with()
        conn.close.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_commit_commits_active_connection(self, get_connection_mock: MagicMock) -> None:
        conn = MagicMock()
        conn.cursor.return_value = MagicMock()
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()
        unit_of_work.__enter__()

        unit_of_work.commit()

        conn.commit.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_rollback_rolls_back_active_connection(self, get_connection_mock: MagicMock) -> None:
        conn = MagicMock()
        conn.cursor.return_value = MagicMock()
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()
        unit_of_work.__enter__()

        unit_of_work.rollback()

        conn.rollback.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_exit_rolls_back_and_closes_resources_when_commit_was_not_called(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()
        unit_of_work.__enter__()

        unit_of_work.__exit__(None, None, None)

        conn.rollback.assert_called_once_with()
        cursor.close.assert_called_once_with()
        conn.close.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_exit_closes_resources_without_rollback_after_commit(self, get_connection_mock: MagicMock) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()
        unit_of_work.__enter__()
        unit_of_work.commit()

        unit_of_work.__exit__(None, None, None)

        conn.commit.assert_called_once_with()
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once_with()
        conn.close.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_exit_still_closes_connection_when_cursor_close_fails(self, get_connection_mock: MagicMock) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        cursor.close.side_effect = RuntimeError("cursor close failed")
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()
        unit_of_work.__enter__()

        unit_of_work.__exit__(None, None, None)

        cursor.close.assert_called_once_with()
        conn.close.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_exit_rolls_back_and_closes_resources_when_exception_occurs(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()
        unit_of_work.__enter__()
        error = RuntimeError("failure")
        call_order: list[str] = []
        conn.rollback.side_effect = lambda: call_order.append("rollback")
        cursor.close.side_effect = lambda: call_order.append("cursor.close")
        conn.close.side_effect = lambda: call_order.append("conn.close")

        unit_of_work.__exit__(RuntimeError, error, None)

        conn.rollback.assert_called_once_with()
        cursor.close.assert_called_once_with()
        conn.close.assert_called_once_with()
        self.assertEqual(call_order, ["rollback", "cursor.close", "conn.close"])

    @patch(f"{MODULE}.get_connection")
    def test_exit_does_not_mask_original_exception_when_rollback_fails(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn
        rollback_error = RuntimeError("rollback failed")
        conn.rollback.side_effect = rollback_error
        original_error = RuntimeError("original failure")

        with self.assertRaises(RuntimeError) as ctx, PostgresUnitOfWork():
            raise original_error

        self.assertIs(ctx.exception, original_error)
        conn.rollback.assert_called_once_with()
        cursor.close.assert_called_once_with()
        conn.close.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_exit_does_not_rollback_after_commit_even_when_exception_occurs(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn
        unit_of_work = PostgresUnitOfWork()
        unit_of_work.__enter__()
        unit_of_work.commit()

        unit_of_work.__exit__(RuntimeError, RuntimeError("failure"), None)

        conn.rollback.assert_not_called()
        cursor.close.assert_called_once_with()
        conn.close.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_exit_raises_rollback_error_on_clean_uncommitted_exit_after_cleanup(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        get_connection_mock.return_value = conn
        rollback_error = RuntimeError("rollback failed")
        conn.rollback.side_effect = rollback_error
        unit_of_work = PostgresUnitOfWork()
        unit_of_work.__enter__()

        with self.assertRaises(RuntimeError) as ctx:
            unit_of_work.__exit__(None, None, None)

        self.assertIs(ctx.exception, rollback_error)
        cursor.close.assert_called_once_with()
        conn.close.assert_called_once_with()
