import subprocess
import unittest


class Cli:
    ics_diff = "ics_diff"
    change_tz = "change_tz"


def run_cli_tool(toolname: str, args: list[str]):
    return subprocess.run([toolname] + args, capture_output=True, text=True, check=False)


class TestCli(unittest.TestCase):
    def test_change_tz(self):
        result = run_cli_tool(Cli.change_tz, ["--version"])
        self.assertEqual(result.returncode, 0)

        result = run_cli_tool(Cli.change_tz, [])
        self.assertEqual(result.returncode, 2)
        self.assertIn("one of the arguments -l/--list ics_file is required", result.stderr)

    def test_ics_diff(self):
        result = run_cli_tool(Cli.ics_diff, ["--version"])
        self.assertEqual(result.returncode, 0)

        result = run_cli_tool(Cli.ics_diff, [])
        self.assertEqual(result.returncode, 2)
        self.assertIn("required: ics_file1, ics_file2", result.stderr)
