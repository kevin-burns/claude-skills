"""Self-contained HTML report for job-feeds.

Inline CSS and JS, no CDN, no network at view time -- the file opens on a
train, survives in an archive, and renders identically years later.

Escaping is the whole risk surface. Job posts are user-submitted content
from eight third-party boards, so every interpolation goes through _esc()
and EVERY attribute is quoted. That second half is not decoration: this
exact defect shipped once in a sibling tool, because html.escape does not
escape spaces, so an unquoted attribute happily accepts an injected
event handler from a value that was technically "escaped".

Deterministic by construction: the generated-at stamp is passed in, never
read from the clock, so identical inputs produce a byte-identical file.
"""

from __future__ import annotations

import html
from datetime import datetime  # noqa: F401  (imported so tests can tripwire it)

# Credit and, where required, a dofollow backlink. Remote OK makes
# attribution a condition of API access and Arbeitnow's meta.terms asks the
# same, so this is a functional requirement rather than politeness.
ATTRIBUTION = {
    "arbeitnow": ("Arbeitnow", "https://www.arbeitnow.com"),
    "jobicy": ("Jobicy", "https://jobicy.com"),
    "remotive": ("Remotive", "https://remotive.com"),
    "remoteok": ("Remote OK", "https://remoteok.com"),
    "nomads": ("Working Nomads", "https://www.workingnomads.com"),
    "4dayweek": ("4 Day Week", "https://4dayweek.io"),
    "wwr": ("We Work Remotely", "https://weworkremotely.com"),
    "pythonorg": ("Python.org Jobs", "https://www.python.org/jobs/"),
}


def _esc(value):
    """Every interpolation goes through here. quote=True is required: the
    company field in real payloads contains a double quote."""
    return html.escape("" if value is None else str(value), quote=True)


def _sources_present(rows):
    """Every source a row came from, including via also_seen_on -- a listing
    found on two boards is still subject to both boards' terms."""
    present = set()
    for row in rows:
        if row.get("source"):
            present.add(row["source"])
        present.update(s for s in (row.get("also_seen_on") or "").split(",") if s)
    return sorted(present)


def render_html(rows, config, window, source_states, generated_at):
    """Render the whole report. `generated_at` is supplied, never derived."""
    lanes = sorted({lane for row in rows for lane in (row.get("lanes") or [])})
    remote_count = sum(1 for row in rows if row.get("remote"))
    starred = sum(1 for row in rows if row.get("highlight"))
    employers = len({row.get("company") for row in rows if row.get("company")})

    out = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>Job feeds</title><style>", _CSS, "</style></head><body>",
        "<h1>Job feeds</h1>",
        f"<div class='sub'>Generated {_esc(generated_at)} &middot; "
        f"{_esc(window)}-day window &middot; {len(rows)} matching role(s)</div>",
        "<div class='kpis'>",
    ]
    for label, value in (("Roles", len(rows)), ("Remote", remote_count),
                         ("Starred", starred), ("Employers", employers),
                         ("Lanes", len(lanes))):
        out.append(f"<div class='kpi'><span>{_esc(label)}</span><b>{_esc(value)}</b></div>")
    out.append("</div>")

    out.append(
        "<div class='controls'>"
        "<input type='text' id='q' placeholder='Filter role, company, location…'>"
        "<select id='lane'><option value=''>All lanes</option>"
        + "".join(f"<option>{_esc(lane)}</option>" for lane in lanes)
        + "</select>"
        "<label><input type='checkbox' id='star'>&#9733; only</label>"
        "<label><input type='checkbox' id='rem'>Remote only</label>"
        "<span id='count'></span></div>")

    out.append("<table id='t'><thead><tr><th>Posted</th><th>Lanes</th><th>Company</th>"
               "<th>Role</th><th>Where</th><th>Also on</th><th>Link</th></tr></thead>"
               "<tbody>")
    for row in rows:
        posted = (row.get("posted_at") or "")[:10]
        lane_list = row.get("lanes") or []
        searchable = " ".join(str(row.get(f) or "")
                              for f in ("title", "company", "location")).lower()
        # Built outside the f-string: backslashes are not permitted inside an
        # f-string expression before Python 3.12, and this project floors at 3.9.
        lane_cell = "".join("<span class='lane'>" + _esc(lane) + "</span>"
                            for lane in lane_list)
        star = "&#9733; " if row.get("highlight") else ""
        out.append(
            f"<tr data-lanes='{_esc(','.join(lane_list))}'"
            f" data-star='{1 if row.get('highlight') else 0}'"
            f" data-remote='{1 if row.get('remote') else 0}'"
            f" data-text='{_esc(searchable)}'>"
            f"<td>{_esc(posted) or '&mdash;'}</td>"
            f"<td>{lane_cell}</td>"
            f"<td>{_esc(row.get('company'))}</td>"
            f"<td>{star}{_esc(row.get('title'))}</td>"
            f"<td>{_esc(row.get('location'))}</td>"
            f"<td class='dim'>{_esc(row.get('also_seen_on'))}</td>"
            f"<td><a href='{_esc(row.get('url'))}' target='_blank'"
            f" rel='noopener'>view</a></td></tr>")
    out.append("</tbody></table>")

    if source_states:
        out.append("<h2>Sources</h2><table class='src'><tbody>")
        for state in source_states:
            out.append(
                f"<tr><td>{_esc(state.get('name'))}</td>"
                f"<td>{_esc(state.get('status'))}</td>"
                f"<td>{_esc(state.get('last_fetch'))}</td>"
                f"<td>{_esc(state.get('row_count') or 0)}</td>"
                f"<td class='dim'>{_esc(state.get('reason'))}</td></tr>")
        out.append("</tbody></table>")

    credits = " &middot; ".join(
        f"<a href='{_esc(url)}' target='_blank'>{_esc(name)}</a>"
        for key, (name, url) in ATTRIBUTION.items() if key in _sources_present(rows))
    out.append(
        "<footer>"
        f"Data from {credits or 'no sources'}. Aggregated for personal use from each "
        "publisher's documented API or feed &mdash; not scraped, not redistributed.<br>"
        f"Lanes: {_esc(', '.join(lane.name for lane in config.lanes))}. "
        f"Excluded: {_esc(', '.join(config.exclude_companies) or 'none')}.<br>"
        "Recruiter contact details are stripped at ingest. Undated roles come from "
        "feeds that publish no date &mdash; shown as &mdash; rather than guessed.<br>"
        "Self-contained: inline CSS/JS, no CDN, opens with no network."
        "</footer>")
    out.append("<script>")
    out.append(_JS)
    out.append("</script></body></html>")
    return "".join(out)


# ---------------------------------------------------------------------------
# Presentation constants, defined ABOVE nothing that uses them at import time
# but placed after the logic on purpose: this is what a browser executes, not
# Python control flow, and there is no reason to read it first.
# ---------------------------------------------------------------------------

_CSS = """
:root{--bg:#f6f7f9;--fg:#212529;--mut:#6c757d;--line:#dee2e6;--card:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#16181c;--fg:#e9ecef;--mut:#9aa0a6;
 --line:#343a40;--card:#1f2226}}
*{box-sizing:border-box}
body{margin:0;padding:1.5rem;background:var(--bg);color:var(--fg);
 font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
h1{font-size:1.5rem;margin:0 0 .25rem}h2{font-size:1rem;margin:2rem 0 .5rem}
.sub{color:var(--mut);font-size:.85rem;margin-bottom:1rem}
.kpis{display:flex;flex-wrap:wrap;gap:.75rem;margin-bottom:1rem}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:.5rem;
 padding:.5rem .9rem;min-width:6.5rem}
.kpi b{display:block;font-size:1.5rem;font-weight:600}
.kpi span{font-size:.68rem;text-transform:uppercase;color:var(--mut)}
.controls{position:sticky;top:0;background:var(--bg);padding:.6rem 0;display:flex;
 flex-wrap:wrap;gap:.5rem;align-items:center;border-bottom:1px solid var(--line);z-index:5}
input,select{background:var(--card);color:var(--fg);border:1px solid var(--line);
 border-radius:.375rem;padding:.3rem .5rem;font-size:.85rem}
input[type=text]{min-width:16rem}
label{font-size:.8rem;color:var(--mut);display:inline-flex;gap:.25rem;align-items:center}
#count{margin-left:auto;font-size:.8rem;color:var(--mut)}
/* No overflow:hidden here. It was added for rounded corners and silently
   disabled position:sticky on the header inside, which is what made the
   header overlap the first rows instead of pinning above them. */
table{width:100%;border-collapse:collapse;background:var(--card);
 border:1px solid var(--line);border-radius:.5rem}
th,td{padding:.35rem .6rem;text-align:left;font-size:.82rem;
 border-bottom:1px solid var(--line);vertical-align:top}
/* The offset cannot be a constant: the controls bar is taller than 3rem
   and WRAPS on narrow screens. The page measures it and sets
   --controls-h; the fallback only applies if the script never runs. */
th{position:sticky;top:var(--controls-h, 3.5rem);background:var(--card);
 font-size:.72rem;text-transform:uppercase;color:var(--mut);z-index:4;
 box-shadow:inset 0 -1px 0 var(--line)}
tr.hide{display:none}
tr:hover td{background:rgba(127,127,127,.07)}
.lane{display:inline-block;background:var(--fg);color:var(--bg);border-radius:.25rem;
 padding:0 .3rem;font-size:.66rem;margin-right:.15rem}
.dim{color:var(--mut);font-size:.75rem}
a{color:inherit}
footer{margin-top:2rem;padding-top:1rem;border-top:1px solid var(--line);
 font-size:.75rem;color:var(--mut)}
@media print{.controls{display:none}}
"""

_JS = """
const rows=[...document.querySelectorAll('#t tbody tr')];
const el=i=>document.getElementById(i);
function apply(){
  const q=el('q').value.trim().toLowerCase(),l=el('lane').value;
  let n=0;
  for(const r of rows){
    const ok=(!q||r.dataset.text.includes(q))
      &&(!l||r.dataset.lanes.split(',').includes(l))
      &&(!el('star').checked||r.dataset.star==='1')
      &&(!el('rem').checked||r.dataset.remote==='1');
    r.classList.toggle('hide',!ok); if(ok)n++;
  }
  el('count').textContent=n+' of '+rows.length;
}
['q','lane','star','rem'].forEach(i=>el(i).addEventListener('input',apply));
apply();

// The sticky column header sits directly beneath the filter bar. That bar
// wraps at narrow widths, so its height is only knowable at runtime --
// a hardcoded offset left the header overlapping the first rows.
const bar=document.querySelector('.controls');
const fit=()=>document.documentElement.style.setProperty(
  '--controls-h', bar.getBoundingClientRect().height+'px');
fit();
addEventListener('resize',fit);
"""
