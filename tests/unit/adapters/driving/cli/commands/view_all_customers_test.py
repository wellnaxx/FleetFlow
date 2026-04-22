import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.view_all_customers import ViewAllCustomers


class ViewAllCustomers_Should(unittest.TestCase):
    def make_cmd(
        self,
        params: list[str] | None = None,
        *,
        authorized: bool = True,
    ) -> ViewAllCustomers:
        cmd = ViewAllCustomers.__new__(ViewAllCustomers)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]

        cmd._authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._authz.has.return_value = authorized  # type: ignore[reportAttributeAccessIssue]

        return cmd

    def test_execute_without_permission_raises(self) -> None:
        cmd = self.make_cmd(authorized=False)

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("CUSTOMER_VIEW", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    def test_no_customers_returns_friendly_message(self) -> None:
        cmd = self.make_cmd(authorized=True)
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        out = cmd.execute()

        self.assertEqual(out, "No customers.")
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_formats_multiple_customers_separated_by_blank_line(self) -> None:
        cmd = self.make_cmd(authorized=True)

        c1 = MagicMock()
        c1.customer_id = 1
        c1.name = "Alice"
        c1.email = "alice@test.com"
        c1.phone_number = "0411111111"

        c2 = MagicMock()
        c2.customer_id = 2
        c2.name = "Bob"
        c2.email = "bob@test.com"
        c2.phone_number = "0422222222"

        c3 = MagicMock()
        c3.customer_id = 3
        c3.name = "Carl"
        c3.email = ""
        c3.phone_number = ""

        cmd._use_case.execute.return_value = [  # type: ignore[reportAttributeAccessIssue]
            c1,
            c2,
            c3,
        ]

        out = cmd.execute()

        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(
            out,
            "Customer 1: Alice (alice@test.com, 0411111111)\n\n"
            "Customer 2: Bob (bob@test.com, 0422222222)\n\n"
            "Customer 3: Carl (, )",
        )

    def test_execute_propagates_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(authorized=True)
        cmd._use_case.execute.side_effect = RuntimeError("db down")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db down", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_ignores_params_if_present(self) -> None:
        cmd = self.make_cmd(params=["ignored"], authorized=True)
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewAllCustomers, "mutates_state", False))
        self.assertFalse(getattr(ViewAllCustomers, "mutates_session", False))


