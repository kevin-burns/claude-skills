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


# --------------------------------------------------------------------------
# Source registry.
#
# Every field name below was read off a live payload on 2026-08-05. Where a
# guess would have been reasonable and wrong, the docstring says so.
# --------------------------------------------------------------------------

from collections import namedtuple  # noqa: E402

Source = namedtuple(
    "Source", "name url required rows normalise rate_limit_seconds paginates")

# GDPR: ads routinely carry a named recruiter's direct email or phone.
# Stripping at ingest rather than at display keeps the operator from
# becoming a controller for third-party personal data in the first place.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"(?<![\w.])(?:\+|00)\d[\d\s().-]{7,}\d(?![\w.])")
_REDACTED = "[contact removed]"


def strip_contacts(text):
    """Remove direct contact details from free text.

    Deliberately narrow. An aggressive number-stripper would eat salary
    bands, version numbers and years of experience -- the substance the
    report exists to show -- so only patterns anchored to an '@' or an
    international dialling prefix are touched.
    """
    if not isinstance(text, str) or not text:
        return text
    return _PHONE.sub(_REDACTED, _EMAIL.sub(_REDACTED, text))


def _text(item, tag):
    return (item.findtext(tag) or "").strip()


def _first_line(text):
    return (text or "").split("\n", 1)[0].strip() or None


def _job(title, company, location, remote, posted_at, url, description, tags, salary=None):
    return {"title": (title or "").strip() or None,
            "company": (company or "").strip() or None,
            "location": (location or "").strip() or None if isinstance(location, str)
            else location,
            "remote": remote,
            "posted_at": posted_at,
            "url": (url or "").strip() or None,
            "description": strip_contacts(description),
            "tags": [t for t in (tags or []) if isinstance(t, str)],
            "salary": salary}


def _rows_key(key):
    return lambda payload: (payload.get(key) or []) if isinstance(payload, dict) else []


def _rows_list(payload):
    return payload if isinstance(payload, list) else []


def _rows_rss(payload):
    return payload.findall(".//item")


def _rows_remoteok(payload):
    """Element [0] is a legal/ToS object, not a posting. It is skipped as
    data but read for attribution -- Remote OK requires a dofollow backlink
    as a condition of API access."""
    return [r for r in _rows_list(payload) if isinstance(r, dict) and r.get("position")]


def n_arbeitnow(r):
    return _job(r.get("title"), r.get("company_name"), r.get("location"),
                bool(r.get("remote")), to_utc(r.get("created_at")), r.get("url"),
                r.get("description"), r.get("tags"))


def n_jobicy(r):
    return _job(r.get("jobTitle"), r.get("companyName"), r.get("jobGeo"), True,
                to_utc(r.get("pubDate")), r.get("url"), r.get("jobDescription"),
                r.get("jobIndustry"))


def n_remotive(r):
    return _job(r.get("title"), r.get("company_name"), r.get("candidate_required_location"),
                True, to_utc(r.get("publication_date")), r.get("url"),
                r.get("description"), r.get("tags"), r.get("salary") or None)


def n_remoteok(r):
    return _job(r.get("position"), r.get("company"), r.get("location"), True,
                to_utc(r.get("date")), r.get("url"), r.get("description"), r.get("tags"))


def n_nomads(r):
    return _job(r.get("title"), r.get("company_name"), r.get("location"), True,
                to_utc(r.get("pub_date")), r.get("url"), r.get("description"), r.get("tags"))


def n_4dayweek(r):
    """`locations` is a list of dicts; a singular `location` key does not
    exist. work_arrangement carries the remote/hybrid/onsite signal."""
    places = r.get("locations") or []
    primary = next((p for p in places if p.get("is_primary")), places[0] if places else {})
    place = ", ".join(x for x in (primary.get("city"), primary.get("country")) if x) or None
    arrangement = (r.get("work_arrangement") or primary.get("work_arrangement") or "").lower()
    return _job(r.get("title"), (r.get("company") or {}).get("name"), place,
                (arrangement == "remote") if arrangement else None,
                to_utc(r.get("posted_at")), r.get("url"), r.get("description"),
                r.get("skills"))


def n_wwr(item):
    """WWR packs the company into the title: 'Stripe: Backend Engineer, AI
    Security'. partition on the FIRST ': ' -- the company never contains one,
    the role sometimes does."""
    raw = _text(item, "title")
    company, separator, title = raw.partition(": ")
    if not separator:
        company, title = "", raw
    return _job(title, company, _text(item, "region") or None, True,
                to_utc(_text(item, "pubDate")), _text(item, "link"),
                item.findtext("description"),
                [c for c in [item.findtext("category")] if c])


def n_pythonorg(item):
    """Company is the LAST comma group, so rpartition, never partition:
    titles carry commas and bracketed qualifiers. These items have no
    pubDate element at all, so posted_at is always None, and the location
    is the description's first line."""
    raw = _text(item, "title")
    title, separator, company = raw.rpartition(", ")
    if not separator:
        title, company = raw, ""
    return _job(title, company, _first_line(item.findtext("description")), None,
                to_utc(_text(item, "pubDate")), _text(item, "link"),
                item.findtext("description"), [])


SOURCES = {
    "arbeitnow": Source(
        "arbeitnow", "https://www.arbeitnow.com/api/job-board-api",
        {"slug", "title", "company_name", "location", "remote", "created_at", "url"},
        _rows_key("data"), n_arbeitnow, None, True),
    "jobicy": Source(
        "jobicy", "https://jobicy.com/api/v2/remote-jobs?count=50&geo=europe",
        {"id", "jobTitle", "companyName", "jobGeo", "pubDate", "url"},
        _rows_key("jobs"), n_jobicy, 3600, False),
    "remotive": Source(
        "remotive", "https://remotive.com/api/remote-jobs",
        {"id", "title", "company_name", "candidate_required_location",
         "publication_date", "url"},
        _rows_key("jobs"), n_remotive, None, False),
    "remoteok": Source(
        "remoteok", "https://remoteok.com/api",
        {"id", "position", "company", "date", "url"},
        _rows_remoteok, n_remoteok, None, False),
    "nomads": Source(
        "nomads", "https://www.workingnomads.com/api/exposed_jobs/",
        {"title", "company_name", "location", "pub_date", "url"},
        _rows_list, n_nomads, None, False),
    "4dayweek": Source(
        "4dayweek", "https://4dayweek.io/api/v2/jobs",
        {"id", "title", "company", "locations", "posted_at", "url"},
        _rows_key("data"), n_4dayweek, None, False),
    "wwr": Source(
        "wwr", "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        set(), _rows_rss, n_wwr, None, False),
    "pythonorg": Source(
        "pythonorg", "https://www.python.org/jobs/feed/rss/",
        set(), _rows_rss, n_pythonorg, None, False),
}
