#!/usr/bin/env python3
"""
validate_json.py — JSON Sanitizer & Validator Script
=====================================================
Part of the json-sanitizer skill.

Usage:
    python validate_json.py <file.json>          # validate a file
    python validate_json.py --stdin              # read from stdin
    python validate_json.py --fix <file.json>    # attempt auto-fix and output corrected JSON
    python validate_json.py --escape "<string>"  # escape a single string value safely

Examples:
    echo '{"key": "C:\\bad\\path"}' | python validate_json.py --stdin
    python validate_json.py broken.json
    python validate_json.py --fix broken.json
    python validate_json.py --escape "He said \"hello\" and left\nNewline here"
"""

import sys
import json
import re
import argparse
import os


# ─────────────────────────────────────────────
# 1. ESCAPE SEQUENCE CHECKER
# ─────────────────────────────────────────────

VALID_ESCAPES = set('"\\bfnrt/')
VALID_ESCAPE_PATTERN = re.compile(r'\\(["\\/bfnrt]|u[0-9a-fA-F]{4})')
INVALID_ESCAPE_PATTERN = re.compile(r'(?<!\\)\\([^"\\/bfnrtu]|u(?![0-9a-fA-F]{4}))')


def find_invalid_escapes(text):
    """
    Returns a list of (position, sequence) tuples for invalid escape sequences found in raw text.
    This scans the raw string content, not a parsed JSON string.
    """
    issues = []
    for match in INVALID_ESCAPE_PATTERN.finditer(text):
        issues.append((match.start(), match.group(0)))
    return issues


# ─────────────────────────────────────────────
# 2. SAFE STRING ESCAPER
# ─────────────────────────────────────────────

def escape_string_value(s):
    """
    Takes a raw Python string and returns a JSON-safe escaped version
    suitable for embedding inside JSON double quotes.
    """
    result = []
    for ch in s:
        cp = ord(ch)
        if ch == '"':
            result.append('\\"')
        elif ch == '\\':
            result.append('\\\\')
        elif ch == '\n':
            result.append('\\n')
        elif ch == '\r':
            result.append('\\r')
        elif ch == '\t':
            result.append('\\t')
        elif ch == '\b':
            result.append('\\b')
        elif ch == '\f':
            result.append('\\f')
        elif cp < 0x20:
            # Other control characters → \uXXXX
            result.append(f'\\u{cp:04x}')
        else:
            result.append(ch)
    return ''.join(result)


# ─────────────────────────────────────────────
# 3. AUTO-FIXER (best-effort)
# ─────────────────────────────────────────────

def attempt_fixes(raw_text):
    """
    Applies a series of best-effort fixes to raw text that is supposed to be JSON.
    Returns (fixed_text, list_of_applied_fixes).
    """
    fixes = []
    text = raw_text

    # Fix 1: Remove single-line comments (// ...)
    no_comment = re.sub(r'//[^\n]*', '', text)
    if no_comment != text:
        fixes.append("Removed single-line comments (// ...)")
        text = no_comment

    # Fix 2: Remove block comments (/* ... */)
    no_block = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    if no_block != text:
        fixes.append("Removed block comments (/* ... */)")
        text = no_block

    # Fix 3: Remove trailing commas before } or ]
    no_trailing = re.sub(r',\s*([}\]])', r'\1', text)
    if no_trailing != text:
        fixes.append("Removed trailing commas before } or ]")
        text = no_trailing

    # Fix 4: Replace single-quoted strings with double-quoted (simple cases)
    # This is a heuristic — only safe for simple non-nested cases
    single_quoted = re.sub(r"(?<![\\])'((?:[^'\\]|\\.)*)'", r'"\1"', text)
    if single_quoted != text:
        fixes.append("Converted single-quoted strings to double-quoted strings (heuristic)")
        text = single_quoted

    # Fix 5: Fix invalid escape sequences like \s, \d, \p, \a, etc.
    def fix_escape(m):
        ch = m.group(1)
        if ch in '"\\bfnrt/':
            return m.group(0)  # Already valid
        elif re.match(r'u[0-9a-fA-F]{4}', ch):
            return m.group(0)  # Valid unicode escape
        else:
            return '\\\\' + ch  # Escape the backslash itself
    fixed_escapes = re.sub(r'\\(.)', fix_escape, text)
    if fixed_escapes != text:
        fixes.append("Fixed invalid escape sequences (e.g. \\s, \\d → \\\\s, \\\\d)")
        text = fixed_escapes

    return text, fixes


# ─────────────────────────────────────────────
# 4. STRUCTURAL ISSUE DETECTOR
# ─────────────────────────────────────────────

def detect_structural_issues(raw_text):
    """
    Returns a list of human-readable issue descriptions found in raw text
    before attempting JSON parsing.
    """
    issues = []

    # Check for comments
    if re.search(r'//[^\n]*', raw_text) or re.search(r'/\*.*?\*/', raw_text, re.DOTALL):
        issues.append("Contains comments (// or /* */), which are not valid in JSON")

    # Check for trailing commas
    if re.search(r',\s*[}\]]', raw_text):
        issues.append("Trailing commas found before } or ] — not allowed in JSON")

    # Check for single-quoted strings
    if re.search(r"(?<![\\])'[^']*'", raw_text):
        issues.append("Single-quoted strings detected — JSON requires double quotes")

    # Check for unquoted keys (heuristic: word chars followed by : not preceded by ")
    if re.search(r'(?<!")(\b[a-zA-Z_][a-zA-Z0-9_]*\b)\s*:', raw_text):
        issues.append("Possibly unquoted keys detected — all JSON keys must be double-quoted strings")

    # Check for invalid escape sequences
    inv = find_invalid_escapes(raw_text)
    if inv:
        for pos, seq in inv[:5]:  # show up to 5
            issues.append(f"Invalid escape sequence `{seq}` at character position {pos}")

    # Check for raw control characters (newlines inside strings are a common issue)
    # Look for raw newlines/tabs that appear to be inside string values
    inside_string = False
    for i, ch in enumerate(raw_text):
        if ch == '"' and (i == 0 or raw_text[i-1] != '\\'):
            inside_string = not inside_string
        if inside_string and ch in ('\n', '\r') and (i == 0 or raw_text[i-1] != '\\'):
            issues.append(f"Raw newline/carriage-return inside a string value near position {i} — use \\n or \\r")
            break  # report once

    return issues


# ─────────────────────────────────────────────
# 5. MAIN VALIDATOR
# ─────────────────────────────────────────────

def validate(raw_text, filename="<input>"):
    print(f"\n{'='*60}")
    print(f"  JSON Sanitizer & Validator")
    print(f"  Input: {filename}")
    print(f"{'='*60}\n")

    # Step 1: Pre-parse structural checks
    structural_issues = detect_structural_issues(raw_text)
    if structural_issues:
        print("⚠️  PRE-PARSE ISSUES DETECTED:")
        for issue in structural_issues:
            print(f"   • {issue}")
        print()

    # Step 2: Try parsing as-is
    try:
        parsed = json.loads(raw_text)
        print("✅  JSON is VALID — parsed successfully.\n")
        print("📄  Pretty-printed output:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
        return True
    except json.JSONDecodeError as e:
        print(f"❌  JSON PARSE ERROR: {e}\n")
        print("   The parser stopped here, but there may be multiple issues.")
        print("   Run with --fix to attempt automatic correction.\n")
        return False


def validate_and_fix(raw_text, filename="<input>"):
    print(f"\n{'='*60}")
    print(f"  JSON Sanitizer & Validator (Auto-Fix Mode)")
    print(f"  Input: {filename}")
    print(f"{'='*60}\n")

    # Step 1: Check if already valid
    try:
        parsed = json.loads(raw_text)
        print("✅  JSON is already VALID — no fixes needed.\n")
        print("📄  Pretty-printed output:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
        return
    except json.JSONDecodeError as e:
        print(f"⚠️  Original JSON has errors: {e}\n")

    # Step 2: Detect issues
    issues = detect_structural_issues(raw_text)
    if issues:
        print("🔍  Issues detected before fixing:")
        for i in issues:
            print(f"   • {i}")
        print()

    # Step 3: Apply fixes
    fixed_text, applied_fixes = attempt_fixes(raw_text)

    if applied_fixes:
        print("🔧  Fixes applied:")
        for f in applied_fixes:
            print(f"   ✓ {f}")
        print()
    else:
        print("   No automatic fixes could be applied.\n")

    # Step 4: Try parsing fixed version
    try:
        parsed = json.loads(fixed_text)
        print("✅  Fixed JSON is VALID!\n")
        print("📄  Fixed & Pretty-printed JSON:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print(f"❌  Auto-fix was not enough. Remaining error: {e}\n")
        print("📄  Partially fixed output (still invalid):")
        print(fixed_text)
        print("\n💡  Tip: Review the escape sequences and structural issues manually.")


# ─────────────────────────────────────────────
# 6. CLI ENTRYPOINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="JSON Sanitizer & Validator — checks escape sequences and structure.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("file", nargs="?", help="Path to a JSON file to validate")
    parser.add_argument("--stdin", action="store_true", help="Read JSON from stdin")
    parser.add_argument("--fix", metavar="FILE", help="Attempt to auto-fix a JSON file")
    parser.add_argument("--escape", metavar="STRING", help="Escape a raw string value for safe use in JSON")

    args = parser.parse_args()

    # Mode: escape a string
    if args.escape:
        escaped = escape_string_value(args.escape)
        print(f'\nEscaped JSON string value:\n"{escaped}"\n')
        print(f'Full JSON example:\n{{"value": "{escaped}"}}')
        return

    # Mode: fix a file
    if args.fix:
        if not os.path.isfile(args.fix):
            print(f"Error: File not found: {args.fix}")
            sys.exit(1)
        with open(args.fix, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
        validate_and_fix(raw, filename=args.fix)
        return

    # Mode: stdin
    if args.stdin:
        raw = sys.stdin.read()
        validate(raw, filename="<stdin>")
        return

    # Mode: file
    if args.file:
        if not os.path.isfile(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
        validate(raw, filename=args.file)
        return

    # No args: show help
    parser.print_help()


if __name__ == "__main__":
    main()
