# JSON Escape Sequences — Complete Reference

This reference is loaded by the json-sanitizer skill when the user needs detailed escape sequence guidance.

---

## The Only Valid Escape Sequences in JSON

According to [RFC 8259 §7](https://datatracker.ietf.org/doc/html/rfc8259#section-7), the following are the **only** escape sequences legal inside a JSON string:

| Escape Sequence | Meaning                        | Unicode Code Point |
|-----------------|--------------------------------|--------------------|
| `\"`            | Double quotation mark          | U+0022             |
| `\\`            | Reverse solidus (backslash)    | U+005C             |
| `\/`            | Solidus (forward slash)        | U+002F             |
| `\b`            | Backspace                      | U+0008             |
| `\f`            | Form feed                      | U+000C             |
| `\n`            | Line feed (newline)            | U+000A             |
| `\r`            | Carriage return                | U+000D             |
| `\t`            | Horizontal tab                 | U+0009             |
| `\uXXXX`        | Unicode code point (hex)       | U+0000 to U+FFFF  |

**Everything else after a backslash is ILLEGAL.** This includes commonly confused ones like:
- `\s` — invalid (use `\\s` if you mean a literal backslash-s, e.g. for a regex)
- `\d` — invalid
- `\p` — invalid
- `\a` — invalid
- `\e` — invalid
- `\0` — invalid (use `\u0000` for null byte)
- `\x41` — invalid (hex escapes are not JSON, only `\uXXXX`)

---

## Unicode Escapes (`\uXXXX`)

- Exactly 4 hex digits required: `\u0041` ✓, `\u41` ✗
- Case-insensitive: `\u0041` and `\u0041` both valid
- For code points above U+FFFF (e.g., emoji), use a **surrogate pair**:
  - 😊 (U+1F60A) → `\uD83D\uDE0A`
  - However, raw UTF-8 emoji are also perfectly valid in JSON — surrogate pairs are only needed if you must produce pure-ASCII output

---

## Control Characters (U+0000 – U+001F)

These must NEVER appear raw inside a JSON string. Always encode them:

| Character | Code Point | JSON Escape     |
|-----------|------------|-----------------|
| Null      | U+0000     | `\u0000`        |
| Bell      | U+0007     | `\u0007`        |
| Backspace | U+0008     | `\b`            |
| Tab       | U+0009     | `\t`            |
| Newline   | U+000A     | `\n`            |
| Vert. Tab | U+000B     | `\u000b`        |
| Form feed | U+000C     | `\f`            |
| Carriage ret | U+000D  | `\r`            |
| Escape    | U+001B     | `\u001b`        |
| Delete    | U+007F     | `\u007f`        |

---

## Language-Specific Gotchas

### Python
Python uses `\n`, `\t`, etc. in its own strings, which look the same as JSON but behave differently in raw string literals. When building JSON manually in Python:

```python
# WRONG — raw string has actual newline
bad = '{"msg": "line1\nline2"}'  # actual newline char = invalid JSON if not in json.dumps

# RIGHT — use json.dumps which handles escaping automatically
import json
good = json.dumps({"msg": "line1\nline2"})
# → '{"msg": "line1\\nline2"}'
```

Always prefer `json.dumps()` over building JSON strings by hand.

### JavaScript
```js
// WRONG — template literals with raw newlines
const bad = `{"msg": "hello
world"}`;

// RIGHT
const good = JSON.stringify({msg: "hello\nworld"});
```

### Windows File Paths
```
# WRONG in JSON
{"path": "C:\Users\john\Desktop"}

# RIGHT — every backslash must be doubled
{"path": "C:\\Users\\john\\Desktop"}
```

### Regex Patterns in JSON
```
# WRONG — \d, \s, \w are not JSON escapes
{"pattern": "\d+\.\d+"}

# RIGHT — backslashes must be escaped
{"pattern": "\\d+\\.\\d+"}
```

---

## Structural Rules Summary

| Rule                              | Valid Example                | Invalid Example              |
|-----------------------------------|------------------------------|------------------------------|
| Keys must be double-quoted        | `{"name": "Alice"}`          | `{name: "Alice"}`            |
| Strings use double quotes only    | `{"k": "value"}`             | `{"k": 'value'}`             |
| No trailing commas                | `[1, 2, 3]`                  | `[1, 2, 3,]`                 |
| No comments                       | `{"x": 1}`                   | `{"x": 1} // note`           |
| Booleans lowercase                | `{"ok": true}`               | `{"ok": True}`               |
| Null lowercase                    | `{"v": null}`                | `{"v": None}`                |
| No undefined                      | `{"v": null}`                | `{"v": undefined}`           |
| No NaN or Infinity                | `{"n": null}`                | `{"n": NaN}`                 |
| Numbers no leading zeros          | `{"n": 10}`                  | `{"n": 010}`                 |

---

## Quick Validator Checklist

Before finalizing JSON, verify:
- [ ] All strings use double quotes
- [ ] All keys are double-quoted
- [ ] Every `\` is either a valid escape or doubled to `\\`
- [ ] No raw newlines, tabs, or control chars inside strings
- [ ] No trailing commas
- [ ] No comments
- [ ] Braces and brackets are balanced
- [ ] Values are only: string, number, boolean, null, array, object
- [ ] `true`, `false`, `null` are lowercase
- [ ] Unicode escapes have exactly 4 hex digits
