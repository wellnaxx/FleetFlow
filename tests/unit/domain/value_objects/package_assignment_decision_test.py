import unittest

from src.domain.enums.package_assignment_rejection_reasons import PackageAssignmentRejectionReason
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.package_assignment_decision import PackageAssignmentDecision


class PackageAssignmentDecision_Should(unittest.TestCase):
    def test_accept_returns_decision_without_rejection_details(self) -> None:
        decision = PackageAssignmentDecision.accept()

        self.assertTrue(decision.accepted)
        self.assertIsNone(decision.reason)
        self.assertIsNone(decision.message)

    def test_reject_returns_decision_with_reason_and_message(self) -> None:
        decision = PackageAssignmentDecision.reject(
            PackageAssignmentRejectionReason.LOCATIONS_NOT_ON_ROUTE,
            "Route does not contain both package locations.",
        )

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, PackageAssignmentRejectionReason.LOCATIONS_NOT_ON_ROUTE)
        self.assertEqual(decision.message, "Route does not contain both package locations.")

    def test_rejects_accepted_decision_with_message(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "accepted assignment"):
            PackageAssignmentDecision(message="Unexpected rejection")

    def test_rejects_rejection_without_non_blank_message(self) -> None:
        for message in (None, "", "   "):
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(
                    DomainValidationError,
                    "requires a message",
                ),
            ):
                PackageAssignmentDecision(
                    reason=PackageAssignmentRejectionReason.TRUCK_CAPACITY_EXCEEDED,
                    message=message,
                )

    def test_rejects_non_enum_rejection_reason(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "rejection reason"):
            PackageAssignmentDecision(
                reason="TRUCK_CAPACITY_EXCEEDED",  # type: ignore[reportArgumentType]
                message="Capacity exceeded.",
            )

    def test_rejects_non_string_message_before_blank_validation(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "message must be a string"):
            PackageAssignmentDecision(
                reason=PackageAssignmentRejectionReason.TRUCK_CAPACITY_EXCEEDED,
                message=123,  # type: ignore[reportArgumentType]
            )
