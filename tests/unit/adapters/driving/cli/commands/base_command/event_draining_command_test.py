import unittest
from unittest.mock import MagicMock

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand


class _EventDrainingCommand(EventDrainingCommand[object]):
    def execute(self) -> str:
        return "ok"


class EventDrainingCommandTests(unittest.TestCase):
    def make_command(self) -> _EventDrainingCommand:
        return _EventDrainingCommand([], object(), MagicMock())

    def test_run_and_drain_drains_recorder_after_success(self) -> None:
        command = self.make_command()
        recorder = MagicMock()

        result = command._run_and_drain(recorder, lambda: "ok")  # pyright: ignore[reportPrivateUsage]

        self.assertEqual(result, "ok")
        command._event_collector.drain.assert_called_once_with((recorder,))  # type: ignore[reportUnknownMemberType]

    def test_run_and_drain_drains_recorder_after_failure_and_reraises_original_error(self) -> None:
        command = self.make_command()
        recorder = MagicMock()

        def fail() -> str:
            raise RuntimeError("operation failed")

        with self.assertRaises(RuntimeError) as ctx:
            command._run_and_drain(recorder, fail)  # pyright: ignore[reportPrivateUsage]

        self.assertEqual(str(ctx.exception), "operation failed")
        command._event_collector.drain.assert_called_once_with((recorder,))  # type: ignore[reportUnknownMemberType]

    def test_run_and_drain_preserves_original_error_when_failure_drain_fails(self) -> None:
        command = self.make_command()
        recorder = MagicMock()
        command._event_collector.drain.side_effect = RuntimeError("publish failed")  # type: ignore[reportAttributeAccessIssue]

        def fail() -> str:
            raise ValueError("bad command")

        with self.assertRaises(ValueError) as ctx:
            command._run_and_drain(recorder, fail)  # pyright: ignore[reportPrivateUsage]

        self.assertEqual(str(ctx.exception), "bad command")
        command._event_collector.drain.assert_called_once_with((recorder,))  # type: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    unittest.main()
