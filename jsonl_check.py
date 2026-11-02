#!/usr/bin/env python3
"""Validate UTF-8 JSON Lines using only the Python standard library."""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class Counts:
    lines: int = 0
    blank: int = 0
    valid: int = 0
    invalid: int = 0


def positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def reject_constant(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant: {value}")


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object key")
        result[key] = value
    return result


def validation_error(line: str, require_object: bool) -> str | None:
    try:
        # Only syntax and the top-level type matter here. Keeping number tokens
        # as strings avoids integer digit limits and floating-point overflow.
        value = json.loads(
            line,
            parse_int=str,
            parse_float=str,
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except json.JSONDecodeError as error:
        return f"{error.msg} (column {error.colno})"
    except ValueError as error:
        return str(error)
    except RecursionError:
        return "nesting exceeds the Python JSON parser's recursion limit"
    if require_object and not isinstance(value, dict):
        return "expected a JSON object"
    return None


def check_stream(
    stream: BinaryIO, source: str, args: argparse.Namespace, counts: Counts
) -> None:
    for raw_line in stream:
        # Decode one physical line at a time, without accepting an initial BOM.
        line = raw_line.decode("utf-8")
        counts.lines += 1
        if not line.strip(" \t\r\n"):
            counts.blank += 1
            if not args.strict_blank:
                continue
            error = "blank line is not allowed (--strict-blank)"
        else:
            error = validation_error(line, args.require_object)
        if error is None:
            counts.valid += 1
        else:
            counts.invalid += 1
            if not args.quiet:
                print(f"{source}:{counts.lines}: {error}")
            if counts.invalid >= args.max_errors:
                break


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate each UTF-8 input line as one JSON value.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Output:
  Validation errors go to stdout as source:line: message (1-based lines).
  One stdout summary per input: source: lines=N blank=N valid=N invalid=N
  Stdin is named <stdin>. Usage and I/O errors go to stderr.
  Counts cover only processed lines; --max-errors stops each input early.
  Skipped blanks count only as blank; strict blanks count as blank and invalid.

Validation policy:
  Duplicate object keys, NaN, Infinity, and a UTF-8 BOM are rejected.
  Arbitrarily large numeric tokens are checked without converting their value.
  Excessive nesting is invalid when it exceeds the Python parser's limit.
  CRLF and an unterminated final line are accepted. Blank means JSON whitespace.
  Invalid UTF-8 is an I/O error. Failed inputs still receive a partial summary.

Exit codes:
  0  All processed input is valid (skipped blanks are allowed).
  1  At least one invalid line.
  2  Usage or I/O error (takes precedence over invalid lines).
""",
    )
    parser.add_argument("files", metavar="FILE", nargs="*", help="input files; '-' or no FILE reads stdin")
    parser.add_argument("--strict-blank", action="store_true", help="count blank lines as invalid")
    parser.add_argument("--require-object", action="store_true", help="require every nonblank value to be a JSON object")
    parser.add_argument("--max-errors", type=positive_integer, default=20, metavar="N", help="stop after N errors per input (positive integer; default: 20)")
    parser.add_argument("--quiet", action="store_true", help="print summaries only; I/O errors still go to stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    # parse_intermixed_args may reinterpret leading-hyphen filenames after
    # consuming '--'. Keep that explicit positional suffix out of its passes.
    positional_suffix = []
    if "--" in arguments:
        separator = arguments.index("--")
        positional_suffix = arguments[separator + 1:]
        arguments = arguments[:separator]
    args = make_parser().parse_intermixed_args(arguments)
    args.files.extend(positional_suffix)
    exit_code = 0
    for filename in args.files or ["-"]:
        source = "<stdin>" if filename == "-" else filename
        counts = Counts()
        try:
            if filename == "-":
                check_stream(sys.stdin.buffer, source, args, counts)
            else:
                with open(filename, "rb") as stream:
                    check_stream(stream, source, args, counts)
        except (OSError, UnicodeError) as error:
            print(f"{source}: I/O error: {error}", file=sys.stderr)
            exit_code = 2
        if counts.invalid:
            exit_code = max(exit_code, 1)
        print(
            f"{source}: lines={counts.lines} blank={counts.blank} "
            f"valid={counts.valid} invalid={counts.invalid}"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
