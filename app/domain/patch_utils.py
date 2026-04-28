"""Parse unified diffs from GitHub-style patches (approximate new-file line numbers)."""

from __future__ import annotations

import re
from collections.abc import Iterator

# @@ -old_start,old_len +new_start,new_len @@
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

# Lines that are not body content
_BINARY_PREFIXES = ("Binary files ", "GIT binary patch")


def iter_added_lines(patch: str | None) -> Iterator[tuple[int, str]]:
    """Yield `(new_line_number, text)` for each added line in a unified diff.

    Line numbers refer to the **post-change** file and are best-effort: they match
    standard unified-diff semantics for typical GitHub patches. Context-only hunks
    advance the new-file pointer without yielding.
    """

    if not patch:
        return

    new_line: int | None = None

    for raw in patch.splitlines():
        if raw.startswith("+++ ") or raw.startswith("--- "):
            continue
        if raw.startswith(_BINARY_PREFIXES):
            new_line = None
            continue

        hunk = _HUNK_HEADER.match(raw)
        if hunk:
            new_line = int(hunk.group(1))
            continue

        if new_line is None:
            continue

        if raw.startswith("+"):
            if raw.startswith("+++"):
                continue
            yield new_line, raw[1:]
            new_line += 1
        elif raw.startswith("-"):
            continue
        elif raw.startswith(" "):
            new_line += 1
        elif raw.startswith("\\"):
            continue
        else:
            continue
