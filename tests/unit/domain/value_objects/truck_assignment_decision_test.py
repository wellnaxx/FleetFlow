import unittest

from src.domain.enums.truck_assignment_rejection_reasons import TruckAssignmentRejectionReason
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.truck_assignment_decision import TruckAssignmentDecision


class TruckAssignmentDecision_Should(unittest.TestCase):
    def test_accept_returns_decision_without_rejection_details(self) -> None:
        decision = TruckAssignmentDecision.accept()

        self.assertTrue(decision.accepted)
        self.assertIsNone(decision.reason)
        self.assertIsNone(decision.message)

    def test_reject_returns_decision_with_reason_and_message(self) -> None:
        decision = TruckAssignmentDecision.reject(
            TruckAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT,
            "range too short",
        )

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, TruckAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT)
        self.assertEqual(decision.message, "range too short")

    def test_rejects_accepted_decision_with_message(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "accepted assignment"):
            TruckAssignmentDecision(message="Unexpected rejection")

    def test_rejects_rejection_without_non_blank_message(self) -> None:
        for message in (None, "", "   "):
            with self.subTest(message=message), self.assertRaisesRegex(
                DomainValidationError,
                "requires a message",
            ):
                TruckAssignmentDecision(
                    reason=TruckAssignmentRejectionReason.TRUCK_CAPACITY_INSUFFICIENT,
                    message=message,
                )

    def test_rejects_non_enum_rejection_reason(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "TruckAssignmentRejectionReason"):
            TruckAssignmentDecision(
                reason="TRUCK_CAPACITY_INSUFFICIENT",  # type: ignore[reportArgumentType]
                message="Capacity exceeded.",
            )

    def test_rejects_non_string_message_before_blank_validation(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "message must be a string"):
            TruckAssignmentDecision(
                reason=TruckAssignmentRejectionReason.TRUCK_CAPACITY_INSUFFICIENT,
                message=123,  # type: ignore[reportArgumentType]
            )
