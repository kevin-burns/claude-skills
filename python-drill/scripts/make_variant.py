#!/usr/bin/env python3
"""Generate a fresh code-reading exercise: a short script plus its input, answer by running it.

Stdlib only. Every family is a template with randomised parts (which lines are filtered, which
index is taken, how the input is shaped, names and values), so the same seed always rebuilds
the same exercise and different seeds give different ones. The answer is never predicted: the
script is run in a subprocess and its stdout, or the exception it dies with, is recorded.

Seen exercises are kept in $PYTHON_DRILL_HOME/variants.json (default
~/.local/share/python-drill/), keyed by family:seed and by a hash of script+input, so `new`
never hands out an exercise already seen.

    make_variant.py families | topics | last
    make_variant.py new [--family F] [--topic T] [--rotate] [--out DIR]
    make_variant.py rebuild FAMILY SEED [--out DIR]     same exercise again (FAMILY/SEED from its answer file)
    make_variant.py selftest [--n 200]                  uniqueness, rebuild and rerun checks

`new` prints the exercise id, script and input paths and the question. The answer (output or
exception, planted problems, topics, family and seed) is in <out>/answers/<id>.json: read it only
after the learner has answered. Exit 3 from `new --topic` means no generator covers that topic.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

RUN_TIMEOUT = 10
DEFAULT_OUT = Path(tempfile.gettempdir()) / "python-drill-variants"


# --------------------------------------------------------------------------- pools

FIRST = [
    "ada",
    "bo",
    "carol",
    "dev",
    "emre",
    "fatma",
    "gus",
    "hana",
    "ivo",
    "jun",
    "kai",
    "lena",
    "milo",
    "nora",
    "omar",
    "pia",
    "quinn",
    "rosa",
    "sven",
    "tara",
]
LAST = ["lane", "chen", "okafor", "berg", "silva", "novak", "ito", "keane", "moreau", "patel"]
DOMAINS = ["example.org", "example.net", "example.com", "mail.example.org"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SUBJECTS = [
    "Hi",
    "Thanks",
    "Update",
    "Re: lunch",
    "Can't make Friday's call",
    "[ops] deploy: r{n} - rollback of the upload tool",
    "Weekly report for team {n}",
    "Re: Re: invoice {n} is overdue",
    "Quick question about the {w} job",
    "[sakai] svn commit: r{n} - {w}/tool/src",
]
WORDS = ["backup", "upload", "billing", "search", "export", "cleanup", "sync", "audit"]
BODY = [
    "Fixed a bug in the {w} tool.",
    "Can't make it, sorry.",
    "Are we still on for Monday?",
    "See the attached log.",
    "Thanks!",
    "The {w} job failed twice overnight.",
    "Rolled back to r{n}.",
    "Please review before Friday.",
]
VARS = ["entities", "found", "items", "results", "names", "values"]
LOOPVARS = ["line", "row", "ln", "text"]


def person(rng: random.Random) -> tuple[str, str, str]:
    first, last = rng.choice(FIRST), rng.choice(LAST)
    addr = f"{first}.{last}@{rng.choice(DOMAINS)}"
    return first.title(), last.title(), addr


def fill(rng: random.Random, template: str) -> str:
    return template.format(n=rng.randint(100, 9999), w=rng.choice(WORDS))


def indent(lines: list[str], n: int) -> list[str]:
    return [(" " * n + x) if x else x for x in lines]


# --------------------------------------------------------------------------- families
# Each returns dict(script, input_name, input_text, topics, kind, question).


def fam_mailbox(rng: random.Random) -> dict:
    msgs = []
    for i in range(rng.randint(3, 6)):
        first, last, addr = person(rng)
        when = dt.datetime(
            rng.randint(2008, 2026),
            rng.randint(1, 12),
            rng.randint(1, 28),
            rng.randint(0, 23),
            rng.randint(0, 59),
            rng.randint(0, 59),
        )
        sep = f"From {addr} {DAYS[when.weekday()]} {MONTHS[when.month - 1]} {when.day:2d} {when:%H:%M:%S} {when.year}"
        header_from = rng.choice([addr, f'"{first} {last}" <{addr}>', f"{first} {last} <{addr}>"])
        body = [fill(rng, b) for b in rng.sample(BODY, rng.randint(1, 3))]
        if rng.random() < 0.3:
            body.insert(0, f"Author: {addr}")
        msgs.append(
            "\n".join(
                [
                    sep,
                    f"Message-ID: <{1000 + i}@{addr.split('@')[1]}>",
                    f"From: {header_from}",
                    f"Subject: {fill(rng, rng.choice(SUBJECTS))}",
                    "",
                    *body,
                    "",
                ]
            )
        )
    text = "\n".join(msgs) + "\n"
    var, lv = rng.choice(VARS), rng.choice(LOOPVARS)
    shape = rng.choice(["index", "index", "slice", "pairs", "body"])
    topics = ["rv.trace-output", "rv.fragile-parsing"]

    if shape == "index":
        cond = rng.choice(
            [
                f'{lv}.startswith("From ")',
                f'{lv}.startswith("From:")',
                f'{lv}.startswith("From")',
                f'{lv}.startswith("Subject:")',
                f'"@" in {lv}',
                f"{lv}.strip()",
            ]
        )
        i = rng.randint(0, 4)
        container = rng.choice(["list", "list", "count", "unique"])
        if container == "list":
            init, add, out = f"{var} = []", f"{var}.append({lv}.split()[{i}])", f"print({var})"
        elif container == "count":
            init = f"{var} = {{}}"
            add = f"key = {lv}.split()[{i}]\n{var}[key] = {var}.get(key, 0) + 1"
            out = f"print({var})"
        else:
            init, add, out = f"{var} = set()", f"{var}.add({lv}.split()[{i}])", f"print(sorted({var}))"
        inner = [f"if {cond}:", *indent(add.split("\n"), 4)]
    elif shape == "slice":
        strip = rng.random() < 0.5
        expr = f"{lv}[9:]" + (".strip()" if strip else "")
        init, out = f"{var} = []", f"print({var})"
        inner = [f'if {lv}.startswith("Subject:"):', f"    {var}.append({expr})"]
        topics = ["rv.trace-output", "core.strings-methods"]
    elif shape == "pairs":
        src = rng.choice(["sep", "header"])
        init, out = f"{var} = []\nsender = None", f"print({var})"
        if src == "sep":
            pick = [f'if {lv}.startswith("From "):', f"    sender = {lv}.split()[1]"]
        else:
            pick = [f'if {lv}.startswith("From:"):', f"    sender = {lv}.split()[1]"]
        strip = ".strip()" if rng.random() < 0.5 else ""
        inner = [*pick, f'if {lv}.startswith("Subject:"):', f"    {var}.append((sender, {lv}[9:]{strip}))"]
    else:  # body
        reset = rng.random() < 0.5
        flush = rng.random() < 0.5
        init = f'{var} = []\nbody = ""\nin_body = False'
        inner = [f'if {lv}.startswith("From "):', "    if body:", f"        {var}.append(body)"]
        if reset:
            inner.append('        body = ""')
        inner += [
            "    in_body = False",
            f'elif {lv}.strip() == "" and not in_body:',
            "    in_body = True",
            "elif in_body:",
            f'    body += {lv}.strip() + " "',
        ]
        out = (f"if body:\n    {var}.append(body)\n" if flush else "") + f"print(len({var}))\nprint({var})"
        topics = ["rv.trace-output", "rv.fragile-parsing", "core.strings-methods"]

    use_with = rng.random() < 0.5
    if use_with:
        loop = ["with open(sys.argv[1]) as f:", f"    for {lv} in f:", *indent(inner, 8)]
    else:
        loop = [f"for {lv} in open(sys.argv[1]):", *indent(inner, 4)]
        topics.append("rv.files-encoding")
    script = "\n".join(["import sys", "", *init.split("\n"), *loop, *out.split("\n")]) + "\n"
    return {
        "script": script,
        "input_name": "mailbox.txt",
        "input_text": text,
        "topics": topics,
        "kind": f"mailbox/{shape}",
        "question": (
            "Would this run as written? What does it print for this input? What would you change before it runs in "
            "production?"
        ),
    }


def fam_regex(rng: random.Random) -> dict:
    lines = []
    for _ in range(rng.randint(4, 6)):
        first, last, addr = person(rng)
        phone = rng.choice(
            [
                f"555-{rng.randint(1000, 9999)}",
                f"0241 555-{rng.randint(1000, 9999)}",
                f"+49 151 5550 {rng.randint(1000, 9999)}",
                f"(030) 555 {rng.randint(1000, 9999)}",
            ]
        )
        lines.append(
            rng.choice(
                [
                    f"{first} {last}: {addr}, call {phone}",
                    f"Support: {addr}",
                    f"Office {phone} ext. {rng.randint(1, 99)}",
                    "No contact details here.",
                    f"old address: {addr}",
                    f"{addr} or {person(rng)[2]}",
                ]
            )
        )
    if rng.random() < 0.5:
        lines.append(lines[0])
    text = "\n".join(lines) + "\n"
    email = rng.choice([r"[\w.]+@[\w.]+", r"([\w.]+)@([\w.]+)", r"\w+@\w+\.\w+"])
    phone = rng.choice([r"\d{3}-\d{4}", r"(\d{3})-(\d{4})", r"\d{3}[-\s]\d{4}"])
    mode = rng.choice(["findall", "search"])
    out = rng.choice(["list", "unique", "count"])
    var = rng.choice(VARS)
    if mode == "findall":
        body = [
            "text = open(sys.argv[1]).read()",
            f'{var} = re.findall(r"{email}", text) + re.findall(r"{phone}", text)',
        ]
    else:
        body = [
            f"{var} = []",
            "for line in open(sys.argv[1]):",
            f'    m = re.search(r"{email}|{phone}", line)',
            "    if m:",
            f"        {var}.append(m.group())",
        ]
    show = {"list": f"print({var})", "unique": f"print(len(set({var})))", "count": f"print(len({var}))"}[out]
    script = "\n".join(["import re", "import sys", "", *body, show]) + "\n"
    return {
        "script": script,
        "input_name": "contacts.txt",
        "input_text": text,
        "topics": ["auto.regex", "rv.trace-output"],
        "kind": f"regex/{mode}",
        "question": (
            "Would this run as written? What does it print for this input? What would you change before it runs in "
            "production?"
        ),
    }


def fam_csv(rng: random.Random) -> dict:
    custs = [f"{rng.choice(LAST).title()} {rng.choice(['GmbH', 'Ltd', 'AG', 'BV'])}" for _ in range(3)]
    rows = ["order_id,customer,amount,date"]
    for i in range(rng.randint(4, 6)):
        amt = rng.choice(
            [
                f"{rng.randint(10, 999)}.{rng.randint(0, 99):02d}",
                str(rng.randint(5, 900)),
                f'"{rng.randint(1, 9)},{rng.randint(100, 999)}.00"'
                if rng.random() < 0.35
                else str(rng.randint(5, 900)),
                "" if rng.random() < 0.3 else f"{rng.randint(10, 99)}.5",
            ]
        )
        date = f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}" if rng.random() < 0.85 else "2026-13-01"
        rows.append(f"{1000 + i},{rng.choice(custs)},{amt},{date}")
    text = "\n".join(rows) + "\n"
    reader = rng.choice(["csv", "split"])
    skip = rng.choice(["check", "check", "next", "next", "slice", "slice", "none"])
    conv = rng.choice(["float(amount)", "float(amount or 0)", "float(amount.replace(',', '') or 0)"])
    agg = rng.choice(["by_customer", "total"])
    var = rng.choice(["totals", "sums", "per_customer"])
    lines = ["import csv", "import sys", ""] if reader == "csv" else ["import sys", ""]
    lines.append(f"{var} = {{}}" if agg == "by_customer" else "total = 0")
    if reader == "csv":
        lines += ['with open(sys.argv[1], newline="") as f:', "    rows = csv.reader(f)"]
        if skip == "next":
            lines.append("    next(rows)")
        it = "rows" if skip != "slice" else "list(rows)[1:]"
        lines.append(f"    for row in {it}:")
        pre = "        "
    else:
        it = "open(sys.argv[1]).readlines()" + ("[1:]" if skip == "slice" else "")
        lines.append(f"for raw in {it}:")
        pre = "    "
        lines.append(pre + 'row = raw.strip().split(",")')
        if skip == "next":
            skip = "check"
    if skip == "check":
        lines += [pre + 'if row[0] == "order_id":', pre + "    continue"]
    lines += [pre + "customer, amount = row[1], row[2]"]
    if agg == "by_customer":
        lines.append(pre + f"{var}[customer] = {var}.get(customer, 0) + {conv}")
        lines.append(f"print({var})")
    else:
        lines.append(pre + f"total += {conv}")
        lines.append("print(total)")
    return {
        "script": "\n".join(lines) + "\n",
        "input_name": "orders.csv",
        "input_text": text,
        "topics": ["auto.csv-json", "rv.fragile-parsing", "rv.trace-output"],
        "kind": f"csv/{reader}-{skip}",
        "question": (
            "Would this run as written? What does it print for this input? What would you change before it runs in "
            "production?"
        ),
    }


def fam_json(rng: random.Random) -> dict:
    items = []
    day = rng.randint(1, 20)
    for _ in range(rng.randint(3, 5)):
        d = day + rng.choice([0, 0, 1])
        item = {"dt_txt": f"2026-11-{d:02d} {rng.choice([9, 12, 15, 18]):02d}:00:00"}
        if rng.random() > 0.08:
            item["main"] = {"temp": round(rng.uniform(-3, 18), rng.choice([0, 1, 2]))}
        item["weather"] = rng.choice(
            [[{"main": rng.choice(["Rain", "Clouds", "Clear", "Snow"])}], []]
            if rng.random() < 0.15
            else [[{"main": rng.choice(["Rain", "Clouds", "Clear"])}]]
        )
        items.append(item)
    text = json.dumps({"city": rng.choice(["Aachen", "Leeds", "Porto", "Graz"]), "list": items}, indent=1) + "\n"
    access_w = rng.choice(['item["weather"][0]["main"]', '(item["weather"] or [{}])[0].get("main")'])
    access_t = rng.choice(['item["main"]["temp"]', 'item.get("main", {}).get("temp")'])
    shape = rng.choice(["by_day", "list", "max_by_day"])
    lines = ["import json", "import sys", "", "data = json.load(open(sys.argv[1]))"]
    if shape == "by_day":
        lines += [
            "summary = {}",
            'for item in data["list"]:',
            '    day = item["dt_txt"][:10]',
            f"    summary[day] = ({access_t}, {access_w})",
            "print(summary)",
        ]
    elif shape == "list":
        lines += [f'print([({access_t}, {access_w}) for item in data["list"]])']
    else:
        lines += [
            "hottest = {}",
            'for item in data["list"]:',
            '    day = item["dt_txt"][:10]',
            f"    temp = {access_t}",
            "    hottest[day] = max(hottest.get(day, temp), temp)",
            "print(hottest)",
        ]
    return {
        "script": "\n".join(lines) + "\n",
        "input_name": "weather.json",
        "input_text": text,
        "topics": ["auto.csv-json", "core.dict-ops", "rv.trace-output"],
        "kind": f"json/{shape}",
        "question": (
            "Would this run as written? What does it print for this input? What would you change before it runs in "
            "production?"
        ),
    }


def fam_logs(rng: random.Random) -> dict:
    levels = ["INFO", "INFO", "WARNING", "ERROR", "DEBUG"]
    lines = []
    for _ in range(rng.randint(5, 8)):
        t = (
            f"2026-11-{rng.randint(1, 28):02d} "
            f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}"
        )
        lvl = rng.choice(levels)
        lines.append(f"{t} {lvl} {rng.choice(WORDS)}: {fill(rng, rng.choice(BODY))}")
        r = rng.random()
        if r < 0.15:
            lines.append("  Traceback (most recent call last):")
        elif r < 0.25:
            lines.append("")
    text = "\n".join(lines) + "\n"
    idx = rng.choice([2, 2, 1, 3])
    cond = rng.choice(['"ERROR" in line', 'line.split()[2] == "ERROR"', "line.strip()", "True"])
    mode = rng.choice(["count_levels", "collect"])
    lines_s = ["import sys", ""]
    if mode == "count_levels":
        lines_s += [
            "counts = {}",
            "for line in open(sys.argv[1]):",
            f"    if {cond}:",
            f"        level = line.split()[{idx}]",
            "        counts[level] = counts.get(level, 0) + 1",
            "print(counts)",
        ]
    else:
        lines_s += [
            "errors = []",
            "for line in open(sys.argv[1]):",
            f"    if {cond}:",
            f"        errors.append(line.split()[{idx}])",
            "print(errors)",
        ]
    return {
        "script": "\n".join(lines_s) + "\n",
        "input_name": "app.log",
        "input_text": text,
        "topics": ["rv.trace-output", "rv.fragile-parsing"],
        "kind": f"logs/{mode}",
        "question": (
            "Would this run as written? What does it print for this input? What would you change before it runs in "
            "production?"
        ),
    }


def fam_gotchas(rng: random.Random) -> dict:
    kind = rng.choice(
        [
            "remove_iter",
            "late_binding",
            "mutable_default",
            "generator",
            "bare_except",
            "finally_return",
            "sort_none",
            "str_immutable",
            "dict_iter",
            "round_half",
        ]
    )
    if kind == "remove_iter":
        prefix = rng.choice(["tmp", "old", "test"])
        names = [
            f"{prefix}-{c}" if rng.random() < 0.55 else rng.choice(["web", "db", "api", "cache"]) + str(i)
            for i, c in enumerate("abcdefg"[: rng.randint(4, 7)])
        ]
        lines = [
            f"hosts = {names!r}",
            "for h in hosts:",
            f'    if h.startswith("{prefix}"):',
            "        hosts.remove(h)",
            "print(hosts)",
        ]
        topics = ["core.list-methods", "core.mutability"]
    elif kind == "late_binding":
        envs = rng.sample(["dev", "test", "stage", "prod", "qa", "demo"], rng.randint(2, 4))
        fixed = rng.random() < 0.3
        lam = "lambda env=env:" if fixed else "lambda:"
        lines = [
            "handlers = []",
            f"for env in {envs!r}:",
            f'    handlers.append({lam} f"deploy to {{env}}")',
            "print([h() for h in handlers])",
        ]
        topics = ["core.scope-closures"]
    elif kind == "mutable_default":
        fn = rng.choice(["add_tag", "collect", "remember"])
        calls = [rng.choice(["'eu'", "'us'", "'apac'", "'emea'"]) for _ in range(rng.randint(2, 4))]
        explicit = rng.randrange(len(calls))
        lines = [f"def {fn}(item, seen=[]):", "    seen.append(item)", "    return seen", ""]
        for j, c in enumerate(calls):
            arg = f"{c}, []" if j == explicit and rng.random() < 0.5 else c
            lines.append(f"r{j} = {fn}({arg})")
        lines.append("print(" + ", ".join(f"r{j}" for j in range(len(calls))) + ")")
        lines.append("print(r0 is r1)")
        topics = ["core.functions", "core.mutability"]
    elif kind == "generator":
        data = [
            f"{rng.choice('abcxyz')}={rng.randint(1, 9)}" if rng.random() < 0.8 else ""
            for _ in range(rng.randint(4, 6))
        ]
        first = rng.choice(["count = sum(1 for _ in rows)", "has_any = any(rows)", "first = next(rows)"])
        lines = [
            f"rows = (r.strip() for r in {data!r} if r)",
            first,
            'keys = [r.split("=")[0] for r in rows]',
            f"print({first.split(' =')[0]}, keys)",
        ]
        topics = ["core.iterators-generators"]
    elif kind == "bare_except":
        inputs = rng.sample(
            ['{"port": "80"}', '{"port": "eighty"}', "{}", "None", '{"port": 443}', '{"port": "8443 "}'], 4
        )
        exc = rng.choice(["except:", "except Exception:", "except ValueError:"])
        lines = [
            "def port(cfg):",
            "    try:",
            '        return int(cfg["port"])',
            f"    {exc}",
            f"        return {rng.choice([8080, 3000, 5000])}",
            "",
            "print(" + ", ".join(f"port({x})" for x in inputs) + ")",
        ]
        topics = ["core.exceptions"]
    elif kind == "finally_return":
        raise_it = rng.random() < 0.7
        body = "        raise FileNotFoundError(path)" if raise_it else '        return "loaded"'
        lines = [
            "def load(path):",
            "    try:",
            body,
            "    finally:",
            f'        return "{rng.choice(["defaults", "empty", "fallback"])}"',
            "",
            f'print(load("/etc/{rng.choice(WORDS)}.conf"))',
        ]
        topics = ["core.exceptions"]
    elif kind == "sort_none":
        nums = [rng.randint(1, 50) for _ in range(rng.randint(4, 6))]
        lines = [f"scores = {nums}", "ranked = scores.sort(reverse=True)", "print(ranked)", "print(scores[:3])"]
        topics = ["core.list-methods", "core.sorting"]
    elif kind == "str_immutable":
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        lines = [
            f'name = "{name}"',
            "name.title()",
            "name.replace(' ', '_')",
            "print(name)",
            "print(name.title().replace(' ', '_'))",
        ]
        topics = ["core.strings-methods"]
    elif kind == "dict_iter":
        d = {w: rng.randint(0, 3) for w in rng.sample(WORDS, 4)}
        lines = [
            f"jobs = {d!r}",
            "for name, failures in jobs.items():",
            "    if failures == 0:",
            "        del jobs[name]",
            "print(jobs)",
        ]
        topics = ["core.dict-ops", "core.mutability"]
    else:  # round_half
        vals = rng.sample([0.5, 1.5, 2.5, 3.5, 2.675, 7 / 2, -0.5, 4.5], 4)
        lines = [f"vals = {vals!r}", "print([round(v) for v in vals])", "print(round(2.675, 2), 7 // 2, -7 // 2)"]
        topics = ["core.types-truthiness"]
    return {
        "script": "\n".join(lines) + "\n",
        "input_name": None,
        "input_text": None,
        "topics": topics,
        "kind": f"gotchas/{kind}",
        "question": "What does this print? Explain why, line by line.",
    }


APOS = ["O'Brien", "D'Souza", "O'Neil"]
# Lines of generated exercise text, filled with str.replace rather than formatting: they are
# SQL that the learner is meant to read, and building them by formatting looks like (and is
# flagged as) injection in the generator itself.
FETCH_LINE = 'print(conn.execute(f"SELECT email FROM users WHERE @COND@").@FETCH@)'
NULL_LINE = 'print(conn.execute("SELECT count(*) FROM users WHERE email @TEST@").fetchone()[0])'


def fam_sql(rng: random.Random) -> dict:
    users = []
    for _ in range(rng.randint(3, 6)):
        first = rng.choice(FIRST).title()
        last = rng.choice(APOS) if rng.random() < 0.25 else rng.choice(LAST).title()
        email = "" if rng.random() < 0.2 else f"{first.lower()}@{rng.choice(DOMAINS)}"
        users.append((first, last, email))
    if rng.random() < 0.3:
        users.append(users[0])
    text = "first,last,email\n" + "\n".join(",".join(u) for u in users) + "\n"
    shape = rng.choice(["inject", "commit", "rerun", "fetch", "null", "executemany", "per_call"])
    load = [
        "import csv",
        "import sqlite3",
        "import sys",
        "from pathlib import Path",
        "",
        'Path("app.db").unlink(missing_ok=True)',
        'conn = sqlite3.connect("app.db")',
        'rows = list(csv.DictReader(open(sys.argv[1], newline="")))',
    ]
    topics = ["rv.sql-safety", "rv.trace-output"]
    if shape == "inject":
        safe = rng.random() < 0.3
        load.append('conn.execute("CREATE TABLE users (first TEXT, last TEXT, email TEXT)")')
        load.append("for r in rows:")
        if safe:
            load.append('    conn.execute("INSERT INTO users VALUES (?, ?, ?)", (r["first"], r["last"], r["email"]))')
        else:
            load.append(
                "    conn.execute(f\"INSERT INTO users VALUES ('{r['first']}', '{r['last']}', '{r['email']}')\")"
            )
        load += ["conn.commit()", 'print(conn.execute("SELECT count(*) FROM users").fetchone()[0])']
    elif shape == "commit":
        where = rng.choice(["none", "loop", "after", "context"])
        load.append('conn.execute("CREATE TABLE users (first TEXT, email TEXT)")')
        load.append("conn.commit()")
        if where == "context":
            load += [
                "with conn:",
                "    for r in rows:",
                '        conn.execute("INSERT INTO users VALUES (?, ?)", (r["first"], r["email"]))',
            ]
        else:
            load += ["for r in rows:", '    conn.execute("INSERT INTO users VALUES (?, ?)", (r["first"], r["email"]))']
            if where == "loop":
                load.append("    conn.commit()")
            elif where == "after":
                load.append("conn.commit()")
        load += [
            'other = sqlite3.connect("app.db")',
            'print(conn.execute("SELECT count(*) FROM users").fetchone()[0],',
            '      other.execute("SELECT count(*) FROM users").fetchone()[0])',
        ]
        topics = ["rv.transactions", "rv.trace-output"]
    elif shape == "rerun":
        schema = rng.choice(["plain", "pk", "unique"])
        verb = rng.choice(["INSERT", "INSERT OR IGNORE", "INSERT OR REPLACE"])
        col = {"plain": "email TEXT", "pk": "email TEXT PRIMARY KEY", "unique": "email TEXT UNIQUE"}[schema]
        load += [
            "",
            "def load():",
            f'    conn.execute("CREATE TABLE IF NOT EXISTS users (first TEXT, {col})")',
            "    for r in rows:",
            f'        conn.execute("{verb} INTO users VALUES (?, ?)", (r["first"], r["email"]))',
            "    conn.commit()",
            "",
            "load()",
            "load()",
            'print(conn.execute("SELECT count(*) FROM users").fetchone()[0])',
        ]
        topics = ["rv.transactions", "rv.trace-output"]
    elif shape == "fetch":
        target = rng.choice(users)[0]
        quoted = rng.random() < 0.5
        cond = f"first = '{target}'" if quoted else f"first = {target}"
        fetch = rng.choice(["fetchone()", "fetchall()", "fetchone()[0]"])
        load += [
            'conn.execute("CREATE TABLE users (first TEXT, email TEXT)")',
            'conn.executemany("INSERT INTO users VALUES (?, ?)", [(r["first"], r["email"]) for r in rows])',
            f'name = "{target}"',
            FETCH_LINE.replace("@COND@", cond.replace(target, "{name}")).replace("@FETCH@", fetch),
        ]
    elif shape == "null":
        load += [
            'conn.execute("CREATE TABLE users (first TEXT, email TEXT)")',
            "for r in rows:",
            '    conn.execute("INSERT INTO users VALUES (?, ?)", (r["first"], r["email"] or None))',
            'print(conn.execute("SELECT count(*), count(email) FROM users").fetchone())',
            NULL_LINE.replace("@TEST@", rng.choice(["= NULL", "IS NULL", "!= ''"])),
        ]
        topics = ["rv.sql-safety", "rv.trace-output", "core.types-truthiness"]
    elif shape == "per_call":
        load += [
            'conn.execute("CREATE TABLE users (first TEXT, email TEXT)")',
            "conn.commit()",
            "",
            "def save(r):",
            '    db = sqlite3.connect("app.db")',
            '    db.execute("INSERT INTO users VALUES (?, ?)", (r["first"], r["email"]))',
        ]
        if rng.random() < 0.6:
            load.append("    db.commit()")
        load += ["", "for r in rows:", "    save(r)", 'print(conn.execute("SELECT count(*) FROM users").fetchone()[0])']
        topics = ["rv.transactions", "rv.structure", "rv.trace-output"]
    else:  # executemany
        col = rng.choice(["first", "last"])
        load += [
            'conn.execute("CREATE TABLE names (name TEXT)")',
            f'names = [r["{col}"] for r in rows]' if rng.random() < 0.6 else f'names = [r["{col}"][0] for r in rows]',
            'conn.executemany("INSERT INTO names VALUES (?)", names)',
            'print(conn.execute("SELECT count(*) FROM names").fetchone()[0])',
        ]
    return {
        "script": "\n".join(load) + "\n",
        "input_name": "users.csv",
        "input_text": text,
        "topics": topics,
        "kind": f"sql/{shape}",
        "question": (
            "Would this run as written? What does it print for this input? What would you change before it runs in "
            "production?"
        ),
    }


def string_line(rng: random.Random) -> tuple[str, str]:
    first, last, addr = person(rng)
    when = dt.datetime(
        rng.randint(2008, 2026),
        rng.randint(1, 12),
        rng.randint(1, 28),
        rng.randint(0, 23),
        rng.randint(0, 59),
        rng.randint(0, 59),
    )
    kinds = {
        "separator": (
            f"From {addr} {DAYS[when.weekday()]} {MONTHS[when.month - 1]} {when.day:2d} {when:%H:%M:%S} {when.year}\n"
        ),
        "header": rng.choice(
            [f"From: {first} {last} <{addr}>\n", f"From: {addr}\n", f"Subject: {fill(rng, rng.choice(SUBJECTS))}\n"]
        ),
        "log": (
            f"{when:%Y-%m-%d %H:%M:%S} {rng.choice(['INFO', 'ERROR', 'WARNING'])} {rng.choice(WORDS)}: "
            f"{fill(rng, rng.choice(BODY))}\n"
        ),
        "csv": (
            f"{rng.randint(1000, 9999)},{last.title()} {rng.choice(['GmbH', 'Ltd'])},"
            f"{rng.randint(5, 999)}.{rng.randint(0, 99):02d},"
            f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        ),
        "path": (
            f"/var/log/{rng.choice(WORDS)}/{rng.choice(WORDS)}-{when:%Y%m%d}.{rng.choice(['log', 'tar.gz', 'csv'])}"
        ),
        "url": (
            f"https://{rng.choice(DOMAINS)}/api/v{rng.randint(1, 3)}/{rng.choice(WORDS)}"
            f"?id={rng.randint(1, 999)}&page={rng.randint(1, 9)}"
        ),
        "kv": f"  {rng.choice(WORDS)}_timeout = {rng.randint(1, 120)}  # seconds\n",
    }
    k = rng.choice(list(kinds))
    return k, kinds[k]


def fam_strings(rng: random.Random) -> dict:
    kind, line = string_line(rng)
    i = rng.randint(-2, 6)
    a, b = rng.randint(0, 12), rng.randint(5, 30)
    ch = rng.choice([":", "@", "/", ",", " ", "=", "?", "."])
    ops = {
        "split_index": f"line.split()[{i}]",
        "split_sep_index": f"line.split({ch!r})[{i}]",
        "split_maxsplit": f"line.split({ch!r}, 1)",
        "split_len": "len(line.split())",
        "split_vs_split_space": "(line.split(), line.split(' '))",
        "slice_from": f"line[{a}:]",
        "slice_range": f"line[{a}:{b}]",
        "slice_neg": f"line[-{rng.randint(2, 8)}:]",
        "slice_step": f"line[::{rng.choice([2, 3, -1])}][:{rng.randint(4, 12)}]",
        "strip_chars": f"line.strip().lstrip({rng.choice(['From', 'Subject', '/var', 'https:/', '0123456789'])!r})",
        "rstrip_newline": f"(line[{a}:], line[{a}:].strip())",
        "partition": f"line.partition({ch!r})",
        "rpartition": f"line.rpartition({ch!r})",
        "find_slice": f"line[line.find({ch!r}) + 1:]",
        "find_missing": f"line.find({rng.choice(['#', '|', ';', '@@'])!r})",
        "index_missing": f"line.index({rng.choice(['#', '|', ';', '@@'])!r})",
        "startswith_tuple": (
            f"line.startswith(({rng.choice(['From ', 'From:', 'Subject:', '/var', 'https'])!r}, "
            f"{rng.choice(['ERROR', '2026', 'From'])!r}))"
        ),
        "removeprefix": f"line.removeprefix({rng.choice(['From: ', 'Subject: ', 'From ', 'https://', '/var/log/'])!r})",
        "split_strip": f"line.split({ch!r}, 1)[-1].strip()",
        "join_split": f"{rng.choice(['-', ', ', ''])!r}.join(line.split({ch!r})[:3])",
        "count": f"line.count({ch!r})",
        "replace_count": f"line.replace({ch!r}, '_', {rng.randint(1, 2)})",
        "unpack": f"a, b = line.split({ch!r})[:2]; result = (a, b)",
    }
    op = rng.choice(list(ops))
    expr = ops[op]
    if op == "unpack":
        body = [f"line = {line!r}", expr.replace("; ", "\n"), "print(repr(result))"]
    else:
        body = [f"line = {line!r}", f"print(repr({expr}))"]
    topics = ["core.strings-methods"] + (["core.slicing"] if "[" in expr else [])
    return {
        "script": "\n".join(body) + "\n",
        "input_name": None,
        "input_text": None,
        "topics": topics,
        "kind": f"strings/{op}",
        "question": "What exactly does this print? (repr() shows quotes, spaces and \\n.) Or what does it raise?",
    }


FAMILIES = {
    "mailbox": fam_mailbox,
    "regex": fam_regex,
    "csv": fam_csv,
    "json": fam_json,
    "logs": fam_logs,
    "gotchas": fam_gotchas,
    "sql": fam_sql,
    "strings": fam_strings,
}


# --------------------------------------------------------------------------- build / run

HELPERS = ["log_progress", "notify_team", "validate_rows", "clean_up", "send_report"]


def add_defects(ex: dict, rng: random.Random) -> None:
    """Interview scripts often do not run as written: an import is missing, or a helper is called
    but never defined, and the input path is hardcoded. Apply those to some exercises."""
    lines = ex["script"].split("\n")
    defects = []
    if ex["input_name"] and rng.random() < 0.35:
        lines = [x.replace("sys.argv[1]", f'"{ex["input_name"]}"') for x in lines]
        defects.append(f'input path hardcoded as "{ex["input_name"]}"; take it from argv or config')
    r = rng.random()
    if r < 0.09:
        body = "\n".join(x for x in lines if not x.startswith(("import ", "from ")))
        used = [x for x in lines if x.startswith("import ") and f"{x.split()[1]}." in body]
        if used:
            victim = rng.choice(used)
            lines.remove(victim)
            defects.append(
                f"`{victim}` is missing: NameError at the first use of `{victim.split()[1]}.` if execution gets there"
            )
    elif r < 0.18:
        helper = rng.choice(HELPERS)
        last = max(i for i, x in enumerate(lines) if x.strip() and not x[0].isspace())
        lines.insert(last, f"{helper}()")
        defects.append(f"`{helper}()` is called but never defined: NameError if execution gets there")
    ex["script"] = "\n".join(lines)
    ex["defects"] = defects
    if defects:
        ex["topics"] = [*ex["topics"], "rv.will-it-run"]


def build(family: str, seed: int) -> dict:
    ex = FAMILIES[family](random.Random(f"{family}:{seed}"))
    if family not in ("gotchas", "strings"):
        add_defects(ex, random.Random(f"{family}:{seed}:defects"))
    else:
        ex["defects"] = []
    ex.update(family=family, seed=seed)
    ex["hash"] = hashlib.sha256((ex["script"] + (ex["input_text"] or "")).encode()).hexdigest()[:16]
    return ex


def run(ex: dict, where: Path) -> dict:
    where.mkdir(parents=True, exist_ok=True)
    (where / "script.py").write_text(ex["script"], encoding="utf-8")
    args = [sys.executable, "-I", "script.py"]
    if ex["input_name"]:
        (where / ex["input_name"]).write_text(ex["input_text"], encoding="utf-8")
        args.append(ex["input_name"])
    try:
        p = subprocess.run(
            args,
            cwd=where,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT,
            env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0"},
            check=False,  # a non-zero exit is the exercise's answer, not an error here
        )
    except subprocess.TimeoutExpired:
        return {"stdout": "", "error": f"timeout after {RUN_TIMEOUT}s", "returncode": None}
    keep = {"script.py", ex["input_name"]}
    for f in where.iterdir():
        if f.name not in keep and f.is_file():
            f.unlink()
    err_lines = [x for x in p.stderr.strip().splitlines() if x.strip()]
    error = err_lines[-1] if p.returncode and err_lines else None
    warnings = [x for x in err_lines if "Warning" in x] if not p.returncode else []
    return {"stdout": p.stdout, "error": error, "warnings": warnings, "returncode": p.returncode}


# --------------------------------------------------------------------------- seen store


def store_path() -> Path:
    home = os.environ.get("PYTHON_DRILL_HOME") or str(Path.home() / ".local/share/python-drill")
    return Path(home) / "variants.json"


def load_seen() -> dict:
    p = store_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"seen": {}}


def save_seen(state: dict) -> None:
    p = store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)
    if json.loads(p.read_text(encoding="utf-8")) != state:
        raise SystemExit(f"read-back mismatch writing {p}")


# --------------------------------------------------------------------------- planted problems

GOTCHA_PROBLEMS = {
    "remove_iter": "removes from the list while iterating over it: items after a removed one are skipped",
    "late_binding": "lambdas created in a loop all read the loop variable's final value (unless bound as a default)",
    "mutable_default": "mutable default argument: one list shared across calls",
    "generator": "a generator can only be consumed once; the second use sees what is left",
    "bare_except": "broad except turns every error (bad value, missing key, None) into the default",
    "finally_return": "return in finally discards the exception (and any earlier return)",
    "sort_none": "list.sort() sorts in place and returns None",
    "str_immutable": "string methods return a new string; the result is thrown away",
    "dict_iter": "deleting from a dict while iterating it raises RuntimeError",
    (
        "round_half"
    ): "round() uses banker's rounding and floats are binary (2.675 -> 2.67); // floors toward minus infinity",
}

STRING_NOTES = {  # the point each string exercise tests; see references/string-ops.md
    "split_index": (
        "split() with no argument splits on runs of whitespace and drops empty strings; [n] counts from 0, negative "
        "from the end; out of range raises IndexError"
    ),
    "split_sep_index": (
        "split(sep) splits on that exact string and keeps empty strings between adjacent separators; out of range "
        "raises IndexError"
    ),
    "split_maxsplit": "split(sep, 1) splits at the first separator only: at most two parts",
    "split_len": "len(line.split()) counts whitespace-separated words; the trailing newline is not a word",
    "split_vs_split_space": (
        "split() collapses runs of spaces and ignores \\n; split(' ') keeps empty strings for double spaces and keeps "
        "the \\n on the last part"
    ),
    "slice_from": "line[a:] is everything from index a to the end, including any trailing \\n; past the end gives ''",
    "slice_range": "line[a:b] is a up to but not including b; out-of-range slice bounds never raise",
    "slice_neg": "line[-n:] is the last n characters, and a trailing \\n is one of them",
    "slice_step": "line[::k] takes every k-th character; [::-1] reverses",
    "strip_chars": (
        "strip/lstrip(chars) remove any of those CHARACTERS from the end(s), not a prefix string: use removeprefix for "
        "a prefix"
    ),
    "rstrip_newline": "a slice keeps the \\n; .strip() removes surrounding whitespace including it",
    "partition": "partition(sep) returns (before, sep, after) at the first sep; if absent, (line, '', '')",
    "rpartition": "rpartition(sep) splits at the LAST sep; if absent, ('', '', line)",
    "find_slice": (
        "find returns the index of the first match, or -1 if absent, so line[find+1:] is the whole line when it is "
        "missing"
    ),
    "find_missing": "find returns -1 when the substring is absent (no exception)",
    "index_missing": "index is find that raises ValueError when the substring is absent",
    "startswith_tuple": "startswith accepts a tuple: True if any prefix matches",
    "removeprefix": "removeprefix (3.9+) removes that exact prefix once, or returns the string unchanged",
    "split_strip": (
        "split(sep, 1)[-1].strip() is the usual 'value after the first colon' idiom; with no sep present it returns "
        "the whole stripped line"
    ),
    "join_split": "sep.join(list) glues the parts with sep between them; join needs strings",
    "count": "count(sub) counts non-overlapping occurrences",
    "replace_count": "replace(old, new, n) replaces only the first n occurrences",
    "unpack": (
        "unpacking needs exactly as many values as names; [:2] guarantees at most two, so fewer than two raises "
        "ValueError"
    ),
}

RULES = [  # (regex on the script, problem text)
    (r"for \w+ in open\(", "file opened without `with`; never closed"),
    (r"open\(sys\.argv\[1\]\)(?!, newline)", "no encoding= on open(); real files are not always UTF-8"),
    (
        r"\.split\(\)\[\d\]",
        "positional field via split()[n]: IndexError on blank/short lines, wrong field when the format shifts",
    ),
    (r'startswith\("From"\)', 'startswith("From") matches both the "From " separator and the "From:" header'),
    (r"\[9:\](?!\.strip)", "slice keeps the trailing newline"),
    (r"body \+= ", "body accumulated across lines: check it is reset per message and the last one is flushed"),
    (r'\.split\(","\)', "hand-splitting CSV breaks on quoted commas; use the csv module"),
    (r"float\(amount\)", 'float(amount) crashes on "" and "1,200.00"'),
    (r"float\(amount or 0\)", "empty amount silently counted as 0; thousands separators crash"),
    (r"\[\"weather\"\]\[0\]", "item['weather'][0] fails on an empty list"),
    (r"\[\"main\"\]\[\"temp\"\]", "item['main']['temp'] fails when 'main' is missing"),
    (r"summary\[day\] = ", "one value per day: later entries for the same day overwrite earlier ones"),
    (r"re\.findall\(r\"[^\"]*\(", "findall with groups returns tuples, not the matched strings"),
    (r"re\.search\(", "search finds only the first match on each line"),
    (r"execute\(f\"", "SQL built with an f-string: injection, and any apostrophe breaks it; use ? parameters"),
    (r"= NULL", "= NULL is never true in SQL; use IS NULL"),
    (r"!= ''", "!= '' also drops NULL rows: any comparison with NULL is unknown, not true"),
    (r"count\(email\)", "count(col) skips NULLs; count(*) counts rows"),
    (r"or None\)", "'' is turned into NULL on insert, so empty and missing look the same"),
    (r"executemany\(.*, names\)", "executemany needs a sequence of tuples; a string is a sequence of characters"),
    (r"unlink\(missing_ok=True\)", "deletes the database on every run"),
    (r'connect\("app\.db"\)', "database path hardcoded; take it from config/env"),
]


def planted_problems(ex: dict) -> list[str]:
    s = ex["script"]
    found = list(ex.get("defects", [])) + [text for pat, text in RULES if re.search(pat, s)]
    kind = ex["kind"].split("/")[1]
    if ex["family"] == "strings":
        return [STRING_NOTES[kind]]
    if ex["family"] == "gotchas":
        found.insert(0, GOTCHA_PROBLEMS[kind])
    if ex["family"] == "csv" and "2026-13-01" in (ex["input_text"] or ""):
        found.append("dates are never validated (the input has 2026-13-01)")
    if ex["family"] == "csv" and kind.endswith("-none"):
        found.append("header row is not skipped")
    if kind == "per_call":
        found.append(
            "opens a new connection on every call and never closes it; open once (main or a class) and pass it in"
        )
        if "    db.commit()" not in s:
            found.append("the per-call connection never commits: those inserts are lost")
    if ex["family"] == "sql":
        if "commit()" not in s and "with conn:" not in s:
            found.append("never commits: other connections (and the next run) see nothing")
        if kind == "rerun" and ("PRIMARY KEY" in s or "UNIQUE" in s) and '"INSERT INTO' in s:
            found.append(
                "plain INSERT against a unique key: the second run raises IntegrityError; use INSERT OR IGNORE or "
                "an upsert"
            )
        if "INSERT" in s and "PRIMARY KEY" not in s and "UNIQUE" not in s and kind == "rerun":
            found.append("no unique key: a second run duplicates rows (INSERT OR REPLACE/IGNORE need a key to act on)")
    if ex["family"] == "logs":
        found.append("level parsed by position; continuation and blank lines break it")
    if ex["family"] != "gotchas":
        found.append("no entry point: module-level code with no __main__ guard or handler (e.g. a Lambda handler)")
        found.append("no error handling, no docstrings, print instead of logging")
    return list(dict.fromkeys(found))


# --------------------------------------------------------------------------- commands


def exercise_id(ex: dict) -> str:
    return "ex-" + ex["hash"][:10]


def write_exercise(ex: dict, out: Path) -> dict:
    """Script and input go in <out>/<id>/, the answer in <out>/answers/<id>.json, so listing or
    showing the exercise directory never shows the answer. The id names neither family nor bug."""
    eid = exercise_id(ex)
    where = out / eid
    result = run(ex, where)
    answer = {k: ex[k] for k in ("family", "seed", "kind", "topics", "hash", "question")}
    answer.update(result)
    answer["planted_problems"] = planted_problems(ex)
    answers = out / "answers"
    answers.mkdir(parents=True, exist_ok=True)
    (answers / f"{eid}.json").write_text(json.dumps(answer, indent=2), encoding="utf-8")
    return {
        "id": eid,
        "script": str(where / "script.py"),
        "input": str(where / ex["input_name"]) if ex["input_name"] else None,
        "question": ex["question"],
        "answer_file": str(answers / f"{eid}.json"),
    }


def covered_topics() -> dict[str, set[str]]:
    cov: dict[str, set[str]] = {}
    for name in FAMILIES:
        for s in range(300):
            for tpc in build(name, s)["topics"]:
                cov.setdefault(tpc, set()).add(name)
    return cov


def last_family(state: dict) -> str | None:
    if not state["seen"]:
        return None
    key = max(state["seen"], key=lambda k: (state["seen"][k].get("date", ""), state["seen"][k].get("n", 0)))
    return key.split(":")[0]


def cmd_new(args) -> None:
    state = load_seen()
    fams = list(FAMILIES)
    if args.family:
        if args.family not in FAMILIES:
            raise SystemExit(f"unknown family {args.family}; have {', '.join(FAMILIES)}")
        fams = [args.family]
    if args.topic:
        cov = covered_topics()
        if args.topic not in cov:
            print(
                f"NO GENERATOR for topic {args.topic}; write a fresh question instead. "
                f"Covered: {', '.join(sorted(cov))}",
                file=sys.stderr,
            )
            sys.exit(3)
        fams = [f for f in fams if f in cov[args.topic]]
        if not fams:
            print(
                f"NO GENERATOR for topic {args.topic} in family {args.family}; "
                f"families covering it: {', '.join(sorted(cov[args.topic]))}",
                file=sys.stderr,
            )
            sys.exit(3)
    if args.rotate and len(fams) > 1:
        last = last_family(state)
        fams = [f for f in fams if f != last] or fams
    seen_hashes = {v["hash"] for v in state["seen"].values()}
    rng = random.Random(secrets.randbits(64))
    for _ in range(2000):
        fam = rng.choice(fams)
        seed = rng.randrange(10**9)
        ex = build(fam, seed)
        if args.topic and args.topic not in ex["topics"]:
            continue
        if f"{fam}:{seed}" in state["seen"] or ex["hash"] in seen_hashes:
            continue
        break
    else:
        raise SystemExit("no unseen exercise found in 2000 tries; widen --family/--topic")
    shown = write_exercise(ex, Path(args.out))
    state["seen"][f"{fam}:{seed}"] = {
        "hash": ex["hash"],
        "kind": ex["kind"],
        "date": dt.date.today().isoformat(),
        "n": len(state["seen"]) + 1,
    }
    save_seen(state)
    shown["seen_total"] = len(state["seen"])
    print(json.dumps(shown, indent=2))


def cmd_rebuild(args) -> None:
    print(json.dumps(write_exercise(build(args.family, args.seed), Path(args.out)), indent=2))


def cmd_last(_args) -> None:
    state = load_seen()
    if not state["seen"]:
        print("no exercises recorded yet")
        return
    rows = sorted(state["seen"].items(), key=lambda kv: (kv[1].get("date", ""), kv[1].get("n", 0)))
    for key, v in rows[-5:]:
        print(f"{v.get('date', '?')}  {key.split(':')[0]}")


def cmd_families(_args) -> None:
    for name in FAMILIES:
        kinds = sorted({build(name, s)["kind"] for s in range(300)})
        print(f"{name:8} {len(kinds)} shapes: {', '.join(k.split('/')[1] for k in kinds)}")


def cmd_topics(_args) -> None:
    for tpc, fams in sorted(covered_topics().items()):
        print(f"{tpc:28} {', '.join(sorted(fams))}")


def cmd_selftest(args) -> None:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name in FAMILIES:
            hashes, kinds, outcomes = set(), set(), {"printed": 0, "raised": 0}
            for seed in range(args.n):
                ex = build(name, seed)
                if build(name, seed)["hash"] != ex["hash"]:
                    print(f"FAIL {name}:{seed} rebuild differs")
                    failures += 1
                hashes.add(ex["hash"])
                kinds.add(ex["kind"])
                if seed < args.runs:
                    a = run(ex, Path(tmp) / f"{name}-{seed}-a")
                    b = run(ex, Path(tmp) / f"{name}-{seed}-b")
                    if (a["stdout"], a["error"]) != (b["stdout"], b["error"]):
                        print(f"FAIL {name}:{seed} output differs between runs")
                        failures += 1
                    if a["error"] and "SyntaxError" in a["error"]:
                        print(f"FAIL {name}:{seed} generated invalid Python: {a['error']}")
                        failures += 1
                    if a["error"] and "timeout" in a["error"]:
                        print(f"FAIL {name}:{seed} timed out")
                        failures += 1
                    outcomes["raised" if a["error"] else "printed"] += 1
            distinct = len(hashes)
            ok = distinct >= args.n * 0.9
            failures += 0 if ok else 1
            print(
                f"{'ok  ' if ok else 'FAIL'} {name:8} {distinct}/{args.n} distinct, {len(kinds)} shapes, "
                f"first {args.runs} run twice: {outcomes['printed']} print, {outcomes['raised']} raise"
            )
    print("selftest:", "PASS" if not failures else f"{failures} failure(s)")
    sys.exit(1 if failures else 0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--family")
    n.add_argument("--topic")
    n.add_argument("--rotate", action="store_true", help="avoid the family used last time")
    n.add_argument("--out", default=str(DEFAULT_OUT))
    r = sub.add_parser("rebuild")
    r.add_argument("family", choices=list(FAMILIES))
    r.add_argument("seed", type=int)
    r.add_argument("--out", default=str(DEFAULT_OUT))
    sub.add_parser("families")
    sub.add_parser("topics")
    sub.add_parser("last")
    s = sub.add_parser("selftest")
    s.add_argument("--n", type=int, default=200)
    s.add_argument("--runs", type=int, default=40)
    args = ap.parse_args()
    {
        "new": cmd_new,
        "rebuild": cmd_rebuild,
        "families": cmd_families,
        "topics": cmd_topics,
        "last": cmd_last,
        "selftest": cmd_selftest,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
