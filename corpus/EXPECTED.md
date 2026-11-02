# Corpus expectations

These expectations use `python3 jsonl_check.py corpus/FILE` with default flags.
Line numbers are one-based physical lines. `none` means no invalid lines.
The validator rejects duplicate object keys and nonstandard NaN/Infinity constants.
Excessive nesting is an explicit parser limit reported as an invalid line.

| File | Expected exit code | Expected invalid-line numbers | Rationale |
| --- | --- | --- | --- |
| `bom.jsonl` | 1 | 1 | A UTF-8 BOM is rejected as content before the JSON value. |
| `comments.jsonl` | 1 | 1, 2 | JSON does not permit standalone or trailing comments. |
| `crlf.jsonl` | 0 | none | CRLF line endings are supported. |
| `deep_nesting.jsonl` | 1 | 1 | Excessive nesting is reported as invalid without a traceback; reading continues. |
| `duplicate_keys.jsonl` | 1 | 1, 2, 3 | Duplicate keys are rejected, including nested and escaped equivalents. |
| `embedded_control.jsonl` | 1 | 1 | An unescaped literal control character inside a string is invalid. |
| `empty.jsonl` | 0 | none | An empty input has no invalid lines. |
| `escaped_controls.jsonl` | 0 | none | Escaped control characters are valid JSON string content. |
| `huge_integer.jsonl` | 0 | none | Valid integer tokens exceed Python's usual digit-conversion limit. |
| `invalid_numbers.jsonl` | 1 | 1, 2, 3, 4 | Leading zeros, leading plus, and missing fractional digits are invalid. |
| `literal_newline_in_string.jsonl` | 1 | 1, 2 | A literal newline splits a string across two invalid physical lines. |
| `mixed_lines.jsonl` | 1 | 3, 6 | Mixed valid, blank, and malformed lines retain physical line numbers. |
| `moderate_nesting.jsonl` | 0 | none | Ordinary nested arrays and objects are valid. |
| `multiple_values.jsonl` | 1 | 1, 2 | Each physical line must contain exactly one JSON value. |
| `no_trailing_newline.jsonl` | 0 | none | The final complete value does not need a trailing newline. |
| `nonfinite_numbers.jsonl` | 1 | 1, 2, 3, 4 | Nonstandard non-finite numeric constants are rejected. |
| `only_blank_lines.jsonl` | 0 | none | Empty and JSON-whitespace-only lines are skipped by default. |
| `single_quotes.jsonl` | 1 | 1 | JSON strings and keys require double quotes. |
| `top_level_values.jsonl` | 0 | none | Numbers, strings, arrays, booleans, and null are allowed by default. |
| `trailing_commas.jsonl` | 1 | 1, 2 | Trailing commas in objects and arrays are invalid JSON. |
| `truncated_final_line.jsonl` | 1 | 2 | An incomplete final value is invalid even without a trailing newline. |
| `unicode_emoji.jsonl` | 0 | none | UTF-8 Unicode, emoji, and escaped Unicode are accepted. |
| `unquoted_keys.jsonl` | 1 | 1 | Object property names must be quoted strings. |
| `valid_objects.jsonl` | 0 | none | Multiple complete objects, including nested values. |
| `very_long_line.jsonl` | 0 | none | A long single string value remains valid. |
