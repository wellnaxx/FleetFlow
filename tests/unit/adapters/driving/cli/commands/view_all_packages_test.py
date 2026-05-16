import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.view_all_packages import ViewAllPackages


class TestViewAllPackages_Should(unittest.TestCase):
    def make_cmd(self) -> ViewAllPackages:
        cmd = ViewAllPackages.__new__(ViewAllPackages)
        cmd._params = []  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: PACKAGE_VIEW_ALL")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as context:
            cmd.execute()

        self.assertIn("PACKAGE_VIEW_ALL", str(context.exception))
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_no_packages_available(self) -> None:
        cmd = self.make_cmd()
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "No packages.")
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]

    def test_with_multiple_packages(self) -> None:
        cmd = self.make_cmd()

        mock_package1 = MagicMock()
        mock_package1.info.return_value = "Package 1 Info"

        mock_package2 = MagicMock()
        mock_package2.info.return_value = "Package 2 Info"

        cmd._use_case.execute.return_value = [  # type: ignore[reportAttributeAccessIssue]
            mock_package1,
            mock_package2,
        ]

        result = cmd.execute()

        self.assertEqual(result, "Package 1 Info\n\nPackage 2 Info")
        cmd._use_case.execute.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        mock_package1.info.assert_called_once_with()
        mock_package2.info.assert_called_once_with()
