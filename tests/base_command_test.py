import unittest
from types import SimpleNamespace

from src.commands.base_command.base_command import BaseCommand


class ConcreteCommand(BaseCommand):
    """Minimal concrete subclass to test BaseCommand wiring."""

    def execute(self) -> str:
        # echo a simple string that uses properties to ensure they work
        return f"{self.params!r} | app={id(self.app_data)} | auth={id(self.auth)}"


class BaseCommand_Should(unittest.TestCase):
    def test_cannot_instantiate_abstract_base_class(self) -> None:
        # Abstract class with abstract method should not instantiate
        with self.assertRaises(TypeError):
            _ = BaseCommand(params=[], app_data=None, auth=None)  # type: ignore[reportArgumentType]

    def test_concrete_subclass_instantiates_and_execute_runs(self) -> None:
        app = SimpleNamespace(name="app")
        auth = SimpleNamespace(name="auth")
        cmd = ConcreteCommand(params=["a", "b"], app_data=app, auth=auth)  # type: ignore[reportArgumentType]

        out = cmd.execute()
        # basic smoke check: execute returns a string containing tuple repr and ids
        self.assertIn("('a', 'b')", out)
        self.assertIn(str(id(app)), out)
        self.assertIn(str(id(auth)), out)

    def test_properties_return_expected_values(self) -> None:
        params = ["x", "y", "z"]
        app = object()
        auth = object()
        cmd = ConcreteCommand(params=params, app_data=app, auth=auth)  # type: ignore[reportArgumentType]

        # params is a tuple copy (immutable view)
        p = cmd.params
        self.assertIsInstance(p, tuple)
        self.assertEqual(p, ("x", "y", "z"))

        # app_data and auth are the same objects passed in
        self.assertIs(cmd.app_data, app)
        self.assertIs(cmd.auth, auth)

    def test_params_is_not_the_same_object_as_internal_list(self) -> None:
        params = ["one", "two"]
        cmd = ConcreteCommand(params=params, app_data=None, auth=None)  # type: ignore[reportArgumentType]

        # The returned tuple must be a distinct object
        p1 = cmd.params
        p2 = cmd.params
        self.assertIsInstance(p1, tuple)
        self.assertIsInstance(p2, tuple)
        self.assertEqual(p1, ("one", "two"))
        # Not the same object (new tuple each call is fine; at least not the list)
        self.assertIsNot(p1, params)
        self.assertNotIsInstance(p1, list)

    def test_params_is_immutable_snapshot_not_affected_by_mutations(self) -> None:
        """
        BaseCommand stores params as a tuple (defensive copy).
        Mutations to the original list must NOT affect .params.
        """
        original = ["a"]
        cmd = ConcreteCommand(params=original, app_data=None, auth=None)  # type: ignore[reportArgumentType]
        self.assertEqual(cmd.params, ("a",))

        # mutate after construction – params should NOT change
        original.append("b")
        self.assertEqual(cmd.params, ("a",))

        # mutate again – still no effect
        original[0] = "A"
        self.assertEqual(cmd.params, ("a",))
