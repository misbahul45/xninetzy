from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[\w+#.\-]+", flags=re.UNICODE)


def matches_query(query: str | None, haystack: str | None) -> bool:
    """Match a free-form query against a haystack using OR-of-tokens semantics.

    Returns True when:
    - query is empty/None/whitespace (no filter)
    - any whitespace-separated token from query appears in haystack (case-insensitive)

    Tokens are extracted by word characters (unicode). Tokens shorter than 3
    characters (e.g. 'c', 'go', 'r') are ignored to avoid noisy single-letter
    false positives. A bare 'intern' query still works because it's length 6.

    Token match uses whole-word boundaries, so 'inter' does NOT match 'intern'.
    This prevents partial-word false positives.
    """
    if haystack is None:
        return False
    if query is None:
        return True
    query = query.strip()
    if not query:
        return True
    haystack_lower = haystack.lower()
    tokens = [t.lower() for t in _TOKEN_RE.findall(query) if len(t) >= 3]
    if not tokens:
        return True
    for tok in tokens:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, haystack_lower):
            return True
    return False


__all__ = ["matches_query"]
