import json
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class DiscoveryConfiguration_Should(unittest.TestCase):
    def test_pytest_discovery_is_constrained_to_tests_and_skips_data(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        pytest_options = pyproject["tool"]["pytest"]["ini_options"]

        self.assertEqual(pytest_options["testpaths"], ["tests"])
        self.assertIn("data", pytest_options["norecursedirs"])
        self.assertIn(".", pytest_options["pythonpath"])

    def test_vscode_unittest_discovery_is_constrained_to_tests(self) -> None:
        settings = json.loads((ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8"))
        args = settings["python.testing.unittestArgs"]

        self.assertTrue(settings["python.testing.unittestEnabled"])
        self.assertEqual(args[args.index("-s") + 1], "./tests")
        self.assertEqual(args[args.index("-t") + 1], ".")
        self.assertEqual(args[args.index("-p") + 1], "*_test.py")

    def test_gitignore_preserves_data_placeholder_and_ignores_runtime_artifacts(self) -> None:
        ignore_lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        self.assertIn("data/*", ignore_lines)
        self.assertIn("!data/.gitkeep", ignore_lines)
        self.assertIn("data/**/state.json.corrupt.*", ignore_lines)
        self.assertIn("data/**/.state.*.json", ignore_lines)
        self.assertIn("data/**/.users.*.json", ignore_lines)
