---
name: json-sanitizer
description: >
  Use this skill whenever the user wants to write, validate, fix, sanitize, or review JSON data.
  Trigger this skill when the user mentions JSON with issues like broken strings, invalid escape
  sequences, unescaped characters, malformed structures, unterminated values, or parse errors.
  Also trigger when they paste raw text/data and want it converted into valid JSON, or when they
  ask "is this JSON valid?", "fix my JSON", "my JSON is broken", "JSON parse error", "escape
  sequences in JSON", "special characters in JSON", or any variation of cleaning/writing JSON
  correctly. Always use this skill proactively when the user shares or requests JSON that may
  contain unsafe or improperly escaped content.
---

# JSON Sanitizer & Validator Skill

This skill helps you write, fix, and validate JSON correctly — with special focus on **escape sequences**, **special characters**, and **structural integrity**. JSON is stricter than it looks, and small mistakes (like a backslash or a newline inside a string) will silently break parsers.

---

## What This Skill Covers

- Identifying and fixing broken or invalid escape sequences
- Handling special characters (newlines, tabs, quotes, backslashes, Unicode, control chars)
- Validating JSON structure (brackets, braces, commas, colons)
- Converting raw/dirty text into safe, valid JSON
- Explaining *why* something is wrong so the user learns the rule
- Producing pretty-printed and minified output on request

---

## Core Rules of Valid JSON (Always Apply These)

### 1. String Escape Sequences — The Most Common Source of Breakage

Inside a JSON string, these characters MUST be escaped with a backslash `\`:

| Character         | Must Be Written As | Why                          |
|-------------------|--------------------|------------------------------|
| Double quote `"`  | `\"`               | Terminates the string early  |
| Backslash `\`     | `\\`               | Starts an escape sequence    |
| Newline           | `\n`               | Raw newlines break parsers   |
| Carriage return   | `\r`               | Same as above                |
| Tab               | `\t`               | Raw tabs are technically invalid |
| Form feed         | `\f`               | Control character            |
| Backspace         | `\b`               | Control character            |
| Unicode (< U+0020)| `\uXXXX`           | Control characters are banned raw |

**Only these escape sequences are valid in JSON:**
`\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t`, `\uXXXX`

Any other `\x` sequence (like `\p`, `\s`, `\d`, `\a`) is **ILLEGAL** in JSON and will cause a parse error.

**Example — Broken vs Fixed:**
```
# BROKEN — raw newline and unescaped backslash
{"message": "Hello
World", "path": "C:\Users\john"}

# FIXED
{"message": "Hello\nWorld", "path": "C:\\Users\\john"}
```

### 2. No Comments Allowed

JSON does not support comments. Neither `//` nor `/* */` are valid.

```
# BROKEN
{"name": "Alice" /* the user */}

# FIXED — remove the comment entirely
{"name": "Alice"}
```

### 3. No Trailing Commas

A trailing comma after the last item in an array or object is invalid.

```
# BROKEN
{"colors": ["red", "blue", "green",]}

# FIXED
{"colors": ["red", "blue", "green"]}
```

### 4. Keys Must Be Double-Quoted Strings

Keys cannot be unquoted identifiers or single-quoted strings.

```
# BROKEN
{name: "Alice", 'age': 30}

# FIXED
{"name": "Alice", "age": 30}
```

### 5. Values Must Be Valid JSON Types

Valid types: `string`, `number`, `boolean` (`true`/`false`), `null`, `array`, `object`.

- Strings use double quotes only
- Numbers have no leading zeros (except `0.x`)
- `undefined`, `NaN`, `Infinity` are NOT valid JSON

```
# BROKEN
{"count": undefined, "score": NaN, "ratio": Infinity}

# FIXED — use null or a real number
{"count": null, "score": null, "ratio": null}
```

### 6. No Binary / Raw Control Characters in Strings

Characters with code points U+0000 through U+001F must be encoded as `\uXXXX`.

```
# BROKEN — contains raw null byte or control char
{"data": "hello[NULL BYTE]world"}

# FIXED
{"data": "hello\u0000world"}
```

---

## How to Approach a User's Request

### When the user shares broken JSON:
1. Parse it mentally (or use the validation script) to identify ALL issues
2. List each problem clearly with its location and the rule it violates
3. Produce the fully corrected JSON
4. Explain each fix briefly so the user understands the pattern

### When the user wants to write JSON from scratch:
1. Clarify the data structure they need
2. Write clean, properly escaped JSON
3. Point out any fields where escape sequences are likely (file paths, multiline text, user input)

### When the user pastes raw text/data to convert:
1. Identify the structure (flat key-value, nested, array, etc.)
2. Escape all special characters in string values
3. Apply all JSON rules
4. Return valid JSON with a summary of what was escaped or changed

### When the user just asks "is this valid?":
1. Check every rule above systematically
2. If valid: confirm it and optionally suggest prettifying
3. If invalid: list all issues and offer to fix them

---

## Output Format

Always return:
1. **Diagnosis** — what was wrong (bullet list, be specific about line/key if possible)
2. **Fixed JSON** — in a fenced code block labeled `json`
3. **Explanation** — brief note on each category of fix applied

If the input was already valid, say so clearly and return the original (optionally pretty-printed).

**Example output structure:**
```
### Issues Found
- Line 2: Raw newline inside string value for key "message" → escaped to `\n`
- Line 3: Unescaped backslash in "path" → escaped to `\\`
- Line 4: Trailing comma after last array element removed

### Fixed JSON
\`\`\`json
{
  "message": "Hello\nWorld",
  "path": "C:\\Users\\john",
  "colors": ["red", "blue"]
}
\`\`\`

### What Changed
- Escape sequences: 2 fixes (newline, backslash)
- Structure: 1 fix (trailing comma)
```

---

## Common Pitfalls Reference

| Scenario                        | Mistake                    | Fix                          |
|---------------------------------|----------------------------|------------------------------|
| Windows file path               | `C:\Users\name`            | `C:\\Users\\name`            |
| Regex pattern                   | `\d+\.\d+`                 | `\\d+\\.\\d+`                |
| Multiline text                  | literal newline            | `\n`                         |
| User input with quotes          | `He said "hi"`             | `He said \"hi\"`             |
| Tab-indented value              | literal tab                | `\t`                         |
| Unicode emoji / special chars   | raw `😊`                   | Allowed as-is (UTF-8 OK) OR `\uD83D\uDE0A` |
| Null byte in data               | `\0` or raw byte           | `\u0000`                     |
| Non-JSON escape like `\s`       | `\s`                       | Either `\\s` or remove       |

> **Note on Unicode:** Emoji and non-ASCII characters (é, ñ, 中, etc.) are valid in JSON strings as raw UTF-8. You only need `\uXXXX` for control characters (U+0000–U+001F) or when the output must be pure ASCII.

---

## Validation Script

Use `scripts/validate_json.py` to programmatically validate any JSON input. Run it when:
- The user pastes a long/complex blob and you want a reliable parse check
- You want to double-check your corrected output before returning it

See the script for usage instructions.
