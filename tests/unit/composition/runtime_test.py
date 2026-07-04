import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.json.config import JSONConfig, set_json_config
from src.adapters.driven.persistence.memory.audit_repository import InMemoryAuditRepository
from src.application.services.auth_service import AuthService
from src.composition.config import AppConfig, PersistenceBackend, set_app_config
from src.composition.runtime import get_audit_repository, get_auth_service, get_container, get_user_repository


class RuntimeCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        get_user_repository.cache_clear()
        get_audit_repository.cache_clear()
        get_auth_service.cache_clear()
        get_container.cache_clear()
        set_app_config(None)
        set_json_config(None)

    def tearDown(self) -> None:
        get_user_repository.cache_clear()
        get_audit_repository.cache_clear()
        get_auth_service.cache_clear()
        get_container.cache_clear()
        set_app_config(None)
        set_json_config(None)

    @patch("src.composition.runtime.JSONUserStore")
    def test_get_user_repository_uses_json_store_for_memory_backend(self, json_store_cls: MagicMock) -> None:
        set_app_config(AppConfig(persistence_backend=PersistenceBackend.MEMORY))
        set_json_config(
            JSONConfig(
                state_path=Path("state.json"),
                export_dir=Path("exports"),
                user_store_path=Path("memory-users.json"),
            )
        )

        repo = get_user_repository()

        self.assertIs(repo, json_store_cls.return_value)
        json_store_cls.assert_called_once_with("memory-users.json")

    @patch("src.composition.runtime.JSONUserStore")
    @patch("src.composition.runtime.PostgresUserRepository")
    def test_get_user_repository_uses_postgres_repository_for_postgres_backend(
        self,
        postgres_repo_cls: MagicMock,
        json_store_cls: MagicMock,
    ) -> None:
        set_app_config(AppConfig(persistence_backend=PersistenceBackend.POSTGRES))

        repo = get_user_repository()

        self.assertIs(repo, postgres_repo_cls.return_value)
        postgres_repo_cls.assert_called_once_with()
        json_store_cls.assert_not_called()

    @patch("src.composition.runtime.JSONUserStore")
    @patch("src.composition.runtime.PostgresUserRepository")
    def test_auth_service_and_token_validation_share_cached_repository(
        self,
        postgres_repo_cls: MagicMock,
        _json_store_cls: MagicMock,
    ) -> None:
        set_app_config(AppConfig(persistence_backend=PersistenceBackend.POSTGRES))

        repo = get_user_repository()
        auth = get_auth_service()

        self.assertIsInstance(auth, AuthService)
        self.assertIs(auth._store, repo)  # pyright: ignore[reportPrivateUsage]
        self.assertIs(get_user_repository(), repo)
        postgres_repo_cls.assert_called_once_with()

    def test_get_audit_repository_uses_in_memory_repository_for_memory_backend(self) -> None:
        set_app_config(AppConfig(persistence_backend=PersistenceBackend.MEMORY))

        repo = get_audit_repository()

        self.assertIsInstance(repo, InMemoryAuditRepository)
        self.assertIs(get_audit_repository(), repo)

    @patch("src.composition.runtime.PostgresAuditRepository")
    def test_get_audit_repository_uses_postgres_repository_for_postgres_backend(
        self,
        postgres_repo_cls: MagicMock,
    ) -> None:
        set_app_config(AppConfig(persistence_backend=PersistenceBackend.POSTGRES))

        repo = get_audit_repository()

        self.assertIs(repo, postgres_repo_cls.return_value)
        self.assertIs(get_audit_repository(), repo)
        postgres_repo_cls.assert_called_once_with()

    @patch("src.composition.runtime.build_container")
    @patch("src.composition.runtime.build_eventing_components")
    @patch("src.composition.runtime.PostgresAuditRepository")
    @patch("src.composition.runtime.PostgresUserRepository")
    def test_get_container_uses_same_auth_service_repository_as_runtime(
        self,
        postgres_repo_cls: MagicMock,
        audit_repo_cls: MagicMock,
        build_eventing_components_mock: MagicMock,
        build_container_mock: MagicMock,
    ) -> None:
        config = AppConfig(persistence_backend=PersistenceBackend.POSTGRES)
        set_app_config(config)

        container = get_container()

        self.assertIs(container, build_container_mock.return_value)
        auth = build_container_mock.call_args.args[0]
        self.assertIs(auth._store, postgres_repo_cls.return_value)  # pyright: ignore[reportPrivateUsage]
        self.assertIs(build_container_mock.call_args.args[2], config)
        self.assertIs(build_container_mock.call_args.args[3], audit_repo_cls.return_value)
        build_eventing_components_mock.assert_called_once_with(audit_repo_cls.return_value)
        postgres_repo_cls.assert_called_once_with()
        audit_repo_cls.assert_called_once_with()
