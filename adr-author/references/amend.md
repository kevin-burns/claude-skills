# When the code and a record disagree, and the code is right

Never delete a record. A replaced record still explains why the code once looked the way it did.

## The deciding question

Ask the author: is the old decision **wrong now**, **narrower than written**, or **right with a
one-off exception**? The answer picks one of the three paths below. If the author is unsure, the
first two are usually the honest answers; an exception that keeps recurring is a narrower decision.

## Wrong now: supersede

1. Write a new record with the next number, in the repo's style, stating the decision as it now
   stands, with a link back: `Supersedes: ADR-4`.
2. In Context, say what changed and why the old decision no longer holds.
3. Change the old record's status to say which record replaced it: `Status: Superseded by ADR-9`.
   Leave the rest of the old record alone.
4. Both edits belong in one change, so nobody reads a successor whose predecessor still says
   Accepted.

## Narrower than written: amend

1. Edit Decision or Consequences so they say what the team actually holds to now.
2. Keep the history in the repo's style: an "Amended" line with the date and one sentence on what
   changed, or the repo's own changelog section if records have one.
3. Do not quietly widen or soften other sentences while editing.

## Right, with a one-off exception

1. Leave the decision as it is.
2. Record the exception the way the team already records them: a commit message line, a note in the
   record, an exceptions list. Look at the history before choosing.
3. If the team has no established way, propose a short note under Consequences ("Exception, DATE:
   the backfill job reads the table once to repair invoice ids") and ask before adding it.
4. Every exception carries its reason.

## After any of the three

Run the self-check on every record you touched, compare each with its approved draft, and show the
author the diff before it is final. List the files changed and suggest a commit message; do not
commit.
