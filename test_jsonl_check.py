"""Black-box tests for the frozen JSONL CLI; stdlib only."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
CLI = ROOT / "jsonl_check.py"
CORPUS = ROOT / "corpus"

# Default CLI invocation: filename -> (exit code, invalid physical line numbers).
# This deliberately duplicates EXPECTED.md so documentation drift fails a test.
EXPECTED = {
    "bom.jsonl": (1, (1,)),
    "comments.jsonl": (1, (1, 2)),
    "crlf.jsonl": (0, ()),
    "deep_nesting.jsonl": (1, (1,)),
    "duplicate_keys.jsonl": (1, (1, 2, 3)),
    "embedded_control.jsonl": (1, (1,)),
    "empty.jsonl": (0, ()),
    "escaped_controls.jsonl": (0, ()),
    "huge_integer.jsonl": (0, ()),
    "invalid_numbers.jsonl": (1, (1, 2, 3, 4)),
    "literal_newline_in_string.jsonl": (1, (1, 2)),
    "mixed_lines.jsonl": (1, (3, 6)),
    "moderate_nesting.jsonl": (0, ()),
    "multiple_values.jsonl": (1, (1, 2)),
    "no_trailing_newline.jsonl": (0, ()),
    "nonfinite_numbers.jsonl": (1, (1, 2, 3, 4)),
    "only_blank_lines.jsonl": (0, ()),
    "single_quotes.jsonl": (1, (1,)),
    "top_level_values.jsonl": (0, ()),
    "trailing_commas.jsonl": (1, (1, 2)),
    "truncated_final_line.jsonl": (1, (2,)),
    "unicode_emoji.jsonl": (0, ()),
    "unquoted_keys.jsonl": (1, (1,)),
    "valid_objects.jsonl": (0, ()),
    "very_long_line.jsonl": (0, ()),
}


class JsonlCheckTests(unittest.TestCase):
    def run_cli(self, *args, data=b"", cwd=ROOT):
        result = subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            timeout=10,
            check=False,
        )
        result.stdout = result.stdout.decode("utf-8")
        result.stderr = result.stderr.decode("utf-8")
        return result

    def errors(self, result, source="<stdin>"):
        pattern = re.compile(r"^" + re.escape(str(source)) + r":(\d+): .+$")
        return tuple(
            int(match.group(1))
            for line in result.stdout.splitlines()
            if (match := pattern.fullmatch(line))
        )

    def assert_summary(self, result, source, lines, blank, valid, invalid):
        expected = (
            f"{source}: lines={lines} blank={blank} valid={valid} invalid={invalid}"
        )
        self.assertIn(expected, result.stdout.splitlines())

    def test_corpus_inventory_and_documented_expectations(self):
        self.assertGreaterEqual(len(EXPECTED), 18)
        self.assertEqual(set(EXPECTED), {p.name for p in CORPUS.glob("*.jsonl")})
        documented = {}
        for line in (CORPUS / "EXPECTED.md").read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
            if len(cells) != 4 or not cells[0].endswith(".jsonl"):
                continue
            self.assertNotIn(cells[0], documented)
            self.assertTrue(cells[3], "Every corpus row needs a rationale")
            numbers = tuple(map(int, re.findall(r"\d+", cells[2])))
            documented[cells[0]] = (int(cells[1]), numbers)
        self.assertEqual(EXPECTED, documented)

    def test_stdin_implicit(self):
        result = self.run_cli(data=b'{}\n\n[1,2]\nbad\n"ok"')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.errors(result), (4,))
        self.assert_summary(result, "<stdin>", 5, 1, 3, 1)

    def test_stdin_dash(self):
        result = self.run_cli("-", data='{"emoji":"🌱"}\r\ntrue'.encode("utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assert_summary(result, "<stdin>", 2, 0, 2, 0)

    def test_empty_stdin(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_summary(result, "<stdin>", 0, 0, 0, 0)

    def test_require_object(self):
        result = self.run_cli(
            "--require-object", data=b'{}\n[]\n"text"\n123\ntrue\nnull\n{"a":1}\n'
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.errors(result), (2, 3, 4, 5, 6))
        self.assert_summary(result, "<stdin>", 7, 0, 2, 5)

    def test_require_object_preserves_json_errors(self):
        result = self.run_cli("--require-object", data=b'{"a":}\n{}\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.errors(result), (1,))
        self.assert_summary(result, "<stdin>", 2, 0, 1, 1)

    def test_blank_lines_skipped(self):
        result = self.run_cli(data=b'\n \t\r\n{}\n\t')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.errors(result), ())
        self.assert_summary(result, "<stdin>", 4, 3, 1, 0)

    def test_strict_blank_lines(self):
        result = self.run_cli("--strict-blank", data=b'\n \t\r\n{}\n\t')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.errors(result), (1, 2, 4))
        self.assert_summary(result, "<stdin>", 4, 3, 1, 3)

    def test_quiet_only_emits_summary(self):
        result = self.run_cli("--quiet", data=b'bad\n{}\n\nwrong\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "<stdin>: lines=4 blank=1 valid=1 invalid=2\n")

    def test_default_error_limit(self):
        result = self.run_cli(data=b'bad\n' * 25 + b'{}\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.errors(result), tuple(range(1, 21)))
        self.assert_summary(result, "<stdin>", 20, 0, 0, 20)

    def test_custom_error_limit_counts_errors_not_lines(self):
        result = self.run_cli("--max-errors", "2", data=b'{}\nbad\n\n[]\nbad\n{}\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.errors(result), (2, 5))
        self.assert_summary(result, "<stdin>", 5, 1, 2, 2)

    def test_strict_blank_respects_error_limit(self):
        result = self.run_cli("--strict-blank", "--max-errors", "1", data=b'\n{}\n')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.errors(result), (1,))
        self.assert_summary(result, "<stdin>", 1, 1, 0, 1)

    def test_error_limit_resets_for_each_input(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            first.write_bytes(b'bad\nbad\n{}\n')
            second.write_bytes(b'{}\nbad\nbad\n')
            result = self.run_cli("--max-errors", "1", first, second)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.errors(result, first), (1,))
        self.assertEqual(self.errors(result, second), (2,))
        self.assert_summary(result, first, 1, 0, 0, 1)
        self.assert_summary(result, second, 2, 0, 1, 1)

    def test_multiple_files_and_stdin(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            first.write_bytes(b'{}\n')
            second.write_bytes(b'[]\nfalse\n')
            result = self.run_cli(first, "-", second, data=b'null\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assert_summary(result, first, 1, 0, 1, 0)
        self.assert_summary(result, "<stdin>", 1, 0, 1, 0)
        self.assert_summary(result, second, 2, 0, 2, 0)
        self.assertEqual(len(result.stdout.splitlines()), 3)

    def test_interspersed_options(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            first.write_bytes(b'{}\n')
            second.write_bytes(b'[]\n')
            result = self.run_cli(first, "--require-object", second, "--quiet")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assert_summary(result, first, 1, 0, 1, 0)
        self.assert_summary(result, second, 1, 0, 0, 1)
        self.assertEqual(len(result.stdout.splitlines()), 2)

    def test_double_dash_allows_leading_hyphen_filename(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "-records.jsonl"
            path.write_bytes(b'{}\n')
            result = self.run_cli("--", path.name, cwd=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assert_summary(result, path.name, 1, 0, 1, 0)

    def test_usage_errors(self):
        cases = [
            ("--max-errors", "0"),
            ("--max-errors", "-1"),
            ("--max-errors", "abc"),
            ("--max-errors", "1.5"),
            ("--max-errors",),
            ("--not-an-option",),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            missing = Path(directory) / "missing.jsonl"
            result = self.run_cli(missing)
        self.assertEqual(result.returncode, 2)
        self.assertIn(str(missing), result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_directory_is_io_error(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            result = self.run_cli(directory)
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_utf8_file(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "invalid-encoding.jsonl"
            path.write_bytes(b'{}\n"\xff"\n')
            result = self.run_cli(path)
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_utf8_stdin(self):
        result = self.run_cli(data=b'"\xff"\n')
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_io_error_takes_precedence_in_either_order(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            invalid = Path(directory) / "invalid.jsonl"
            missing = Path(directory) / "missing.jsonl"
            invalid.write_bytes(b'bad\n')
            for paths in [(invalid, missing), (missing, invalid)]:
                with self.subTest(paths=paths):
                    result = self.run_cli(*paths)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(str(missing), result.stderr)
                    self.assertEqual(self.errors(result, invalid), (1,))

    def test_quiet_keeps_io_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            result = self.run_cli("--quiet", Path(directory) / "missing.jsonl")
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr)

    def test_help(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        for flag in ["--strict-blank", "--require-object", "--max-errors", "--quiet"]:
            self.assertIn(flag, result.stdout)
        self.assertIn("stdin", result.stdout.lower())
        self.assertIn("stdout", result.stdout.lower())
        for code in ["0", "1", "2"]:
            self.assertRegex(result.stdout, r"\b" + code + r"\b")


def corpus_test(filename, exit_code, invalid_lines):
    def test(self):
        path = CORPUS / filename
        result = self.run_cli(path)
        self.assertEqual(result.returncode, exit_code, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.errors(result, path), invalid_lines)
        self.assertRegex(
            result.stdout.splitlines()[-1],
            r"^" + re.escape(str(path)) + r": lines=\d+ blank=\d+ valid=\d+ invalid=\d+$",
        )
    return test


for _filename, (_exit_code, _invalid_lines) in EXPECTED.items():
    setattr(
        JsonlCheckTests,
        "test_corpus_" + Path(_filename).stem.replace("-", "_"),
        corpus_test(_filename, _exit_code, _invalid_lines),
    )


if __name__ == "__main__":
    unittest.main()
