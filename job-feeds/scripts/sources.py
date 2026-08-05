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


# --------------------------------------------------------------------------
# Deduplication.
#
# The rule below was measured against 424 rows fetched live from all eight
# feeds on 2026-08-05, not reasoned about in the abstract, because the two
# obvious rules are both wrong:
#
#   company + title + raw location -> 0 cross-source merges. The same job on
#     two boards carries different location text, so nothing ever matches.
#   company + title (no location)  -> 3 cross-source merges but 7 FALSE ones.
#     Grafana Labs runs the same platform-engineer opening in the UK, Spain
#     and Ireland; Peroptyx runs one in Sweden, Australia, Canada and Japan.
#     Those are separate applications, not duplicates.
#
# company + title + loc_bucket gives 3 merges and 0 false ones.
# --------------------------------------------------------------------------

import hashlib  # noqa: E402

# (m/w/d) and its variants are German job-ad gender markers -- maennlich /
# weiblich / divers. The same posting is syndicated with and without them,
# so leaving them in splits one job into two.
_NOISE = re.compile(
    r"\((?:m/w/d|m/f/d|w/m/d|d/m/w|m/w/x|all genders?|remote|hybrid|on-?site)\)"
    r"|\b(?:m/w/d|m/f/d|w/m/d)\b", re.IGNORECASE)
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")

_MODE = re.compile(
    r"\b(fully remote|work from home|wfh|remote|hybrid|on ?site|onsite)\b", re.IGNORECASE)
_ANYWHERE = re.compile(r"\b(anywhere|worldwide|global)\b", re.IGNORECASE)
_REGION = re.compile(
    r"\b(americas?|europe|asia|africa|oceania|apac|emea|latin america|"
    r"north america|south america)\b", re.IGNORECASE)


def norm(value):
    """Lowercase, drop gender markers and punctuation, collapse whitespace."""
    text = value.lower() if isinstance(value, str) else ""
    text = _NOISE.sub(" ", text)
    text = _PUNCT.sub(" ", text)
    return _WS.sub(" ", text).strip()


def loc_bucket(location):
    """Coarse location identity for deduplication.

    The work-mode marker is stripped FIRST, deliberately: 'Sweden - Remote'
    is Sweden, not anywhere. Testing for the bare word 'remote' before
    stripping merges Sweden with Japan, which are two real and distinct
    Peroptyx postings in the same payload.

    What remains collapses to one token only if it is empty, names an
    anywhere-synonym, or lists two or more regions -- a spread rather than
    a place. A single region ('Europe') is a place and survives.
    """
    text = _WS.sub(" ", _MODE.sub(" ", norm(location))).strip()
    if not text or _ANYWHERE.search(text):
        return "anywhere"
    if len({match.lower() for match in _REGION.findall(text)}) >= 2:
        return "anywhere"
    return text


def dedupe_key(company, title, location):
    """Stable 16-char identity for a posting, shared across sources."""
    joined = "|".join((norm(company), norm(title), loc_bucket(location)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
