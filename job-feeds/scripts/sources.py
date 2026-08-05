"""Source registry and per-source normalisers for job-feeds.

This is the only module that knows a given upstream exists. Everything
downstream consumes the common job dict produced here, so adding a feed
means adding one entry to SOURCES and one normalise function -- nothing
else in the codebase changes.

Standard library only.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import re

_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def to_utc(value):
    """Any feed timestamp -> 'YYYY-MM-DDTHH:MM:SSZ', or None.

    Normalising to UTC at ingest is load-bearing rather than tidy: rows are
    compared, bucketed and sorted by this string, and a lexicographic
    compare across mixed offsets silently misorders. Three of the eight
    feeds return non-UTC offsets.

    datetime.fromisoformat did not accept a trailing 'Z' until Python 3.11
    and this project supports 3.9, so 'Z' is rewritten explicitly rather
    than relied upon.
    """
    # bool is a subclass of int -- True would otherwise parse as 1970-01-01.
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return dt.datetime.fromtimestamp(value, dt.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None
    if _DATE_ONLY.match(text):
        text += "T00:00:00"
    iso = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text

    try:
        parsed = dt.datetime.fromisoformat(iso.replace(" ", "T", 1))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
