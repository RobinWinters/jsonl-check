# JSONL Check

A small, dependency-free command-line validator for JSON Lines: each nonblank
physical line must contain exactly one JSON value. It reports invalid lines and
a separate summary for each input.

## Install

No installation or dependencies are needed. Copy `jsonl_check.py` and run it
with Python 3.10 or newer.

## Usage

```sh
python3 jsonl_check.py records.jsonl
python3 jsonl_check.py first.jsonl second.jsonl
python3 jsonl_check.py < records.jsonl
python3 jsonl_check.py - < records.jsonl
python3 jsonl_check.py --require-object records.jsonl
python3 jsonl_check.py --strict-blank --max-errors 5 records.jsonl
python3 jsonl_check.py --quiet records.jsonl
python3 jsonl_check.py --help
```

With no file arguments, or with `-` as a file argument, the utility reads stdin.
Its diagnostic source name is `<stdin>`. Use `--` before a filename that starts
with a hyphen.

Options:

- `--require-object`: require every nonblank value to be a JSON object.
- `--strict-blank`: treat blank lines as invalid; otherwise skip them.
- `--max-errors N`: stop reading each input after N invalid lines. N must be
  positive; the default is 20. Other inputs are still checked.
- `--quiet`: suppress individual validation errors and print summaries only.
  Usage and I/O errors are still reported.
- `--help`: show usage, validation policy, and exit codes.

Validation errors go to stdout as `source:line: message`, with line numbers
starting at one. Summaries also go to stdout:

```text
records.jsonl: lines=4 blank=1 valid=2 invalid=1
```

Counts cover only the lines actually processed, including the line that reaches
the error limit. A strict blank line increments both `blank` and `invalid`.
Otherwise, blank lines increment only `blank`. An empty input is valid with all
counts zero. Blank lines contain only JSON whitespace (space, tab, carriage
return, or line feed). Usage and I/O diagnostics go to stderr. An input that
fails to open receives a zero-count summary; an input that fails while reading
receives a partial summary, excluding any undecodable line. Processing continues
with subsequent inputs.

## Validation policy

Files use UTF-8. CRLF line endings and a missing final newline are supported.
Strings, numbers, arrays, booleans, and null are accepted as top-level values
unless `--require-object` is set. The utility validates syntax, not an application
schema.

Duplicate object keys are rejected, including equivalent keys expressed through
JSON escapes. Nonstandard constants `NaN`, `Infinity`, and `-Infinity` are
rejected. A UTF-8 byte order mark (BOM) is rejected. Literal control characters,
trailing commas, single quotes, and multiple values on one line are invalid.
Huge integer tokens are accepted without converting them to Python integers.

Excessive nesting that exceeds the Python decoder's recursion limit is reported
as an invalid line. The exact nesting limit depends on the Python runtime. The
validator reads one physical line at a time; it has no fixed line-length limit,
so a very large line still requires corresponding memory.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | All processed inputs are valid, including skipped blank lines. |
| 1 | At least one invalid line was found. |
| 2 | A usage or I/O error occurred, including invalid UTF-8. This takes precedence over validation errors. |

## Corpus and tests

`corpus/` contains small adversarial and valid JSONL fixtures. Cases cover
malformed syntax, duplicate keys, nonstandard numeric constants, huge integers,
deep nesting, Unicode and emoji, BOM, CRLF, missing final newline, empty and blank
inputs, top-level value types, truncated input, literal control characters, and
long lines. `corpus/EXPECTED.md` records each fixture's default exit code and
invalid line numbers. Expectations are also encoded in the test suite.

Run the full standard-library test suite from this directory:

```sh
python3 -m unittest -v
```

The suite checks every corpus file and exercises stdin, options, summaries,
multiple inputs, and error handling.

## FROZEN RELEASE

This is a frozen release: no updates, no support, no roadmap, and no issues
triaged. Use the supplied utility as-is.

## Support

Voluntary support, a tip, or pay-what-you-want for this utility is welcome.
It does not purchase support, updates, or future work.

Support link: https://buy.stripe.com/bJe28qgTC3es7VmepLa7C01

