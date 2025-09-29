import unittest
from unittest.mock import patch
from types import SimpleNamespace

from src.core.command_factory import CommandFactory


class _DummyCmd:
    """Minimal command class compatible with BaseCommand signature."""
    def __init__(self, params, app_data, auth):
        self._params = params
        self._app_data = app_data
        self._auth = auth

    def execute(self):
        return f"ok:{self._params!r}"


class CommandFactory_Should(unittest.TestCase):
    def make_factory(self):
        app = SimpleNamespace(name="app1")
        auth = SimpleNamespace(name="auth1")
        return CommandFactory(data=app, auth=auth), app, auth

    def test_no_command_given_raises(self):
        cf, *_ = self.make_factory()
        with self.assertRaises(ValueError) as ctx:
            cf.create("   ")
        self.assertIn("No command given", str(ctx.exception))

    def test_unknown_command_raises(self):
        cf, *_ = self.make_factory()
        with self.assertRaises(ValueError) as ctx:
            cf.create("doesnotexist arg1 arg2")
        self.assertIn("Invalid command name: doesnotexist", str(ctx.exception))

    def test_case_insensitive_name_and_param_parsing_with_quotes(self):
        cf, app, auth = self.make_factory()
        with patch('src.core.command_factory._REGISTRY', {'dummy': _DummyCmd}):
            # Mix case name; shlex should preserve quoted segments and spaces
            cmd = cf.create('DuMmY "SYD" MEL "John Doe" "email with space@x.com"')
            self.assertIsInstance(cmd, _DummyCmd)
            # Params preserved as parsed by shlex
            self.assertEqual(cmd._params, ["SYD", "MEL", "John Doe", "email with space@x.com"])
            # Wiring
            self.assertIs(cmd._app_data, app)
            self.assertIs(cmd._auth, auth)

    def test_extra_whitespace_and_simple_params(self):
        cf, *_ = self.make_factory()
        with patch('src.core.command_factory._REGISTRY', {'dummy': _DummyCmd}):
            cmd = cf.create("   dummy   A   B   C   ")
            self.assertEqual(cmd._params, ["A", "B", "C"])

    def test_update_app_replaces_app_reference_for_future_commands(self):
        cf, app1, auth1 = self.make_factory()
        app2 = SimpleNamespace(name="app2")
        cf.update_app(app2)

        with patch('src.core.command_factory._REGISTRY', {'dummy': _DummyCmd}):
            cmd = cf.create("dummy X")
            self.assertIs(cmd._app_data, app2)   # uses the updated app
            self.assertIs(cmd._auth, auth1)      # auth unchanged
