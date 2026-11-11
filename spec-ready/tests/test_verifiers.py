"""Verifiers: who decides that a turn of the person's states a planning item.

The script calls the verifier and builds its brief, so the agent cannot steer or skip it. Every
answer must quote the span it relied on; a yes whose span is not in the turn is not a yes.
Nothing here touches the network or a real model: runners and openers are injected.
"""

import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from items import DEFAULT_ITEMS
from verifiers import (
    AnswerFileVerifier,
    HeadlessClaude,
    OllamaVerifier,
    Verdict,
    apply_quote_rule,
    build_brief,
    combine,
    parse_answer,
    select_verifiers,
)

ANTI = next(i for i in DEFAULT_ITEMS if i.key == "anti_goal")
TURN = "It fails if it turns into a clone of someone else’s app, even if it “works”."


class FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout, self.returncode, self.stderr = stdout, returncode, ""


def envelope(result: str, is_error: bool = False) -> str:
    return json.dumps({"type": "result", "subtype": "success", "is_error": is_error, "result": result})


def test_quote_rule_yes_without_matching_span_is_unsure():
    v = apply_quote_rule(Verdict("yes", 0.9, "a clone of a competitor", "x"), TURN)
    assert v.answer == "unsure" and "span" in v.reason


def test_quote_rule_normalises_typography():
    v = apply_quote_rule(Verdict("yes", 0.9, "a clone of someone else's app, even if it \"works\"", "x"), TURN)
    assert v.answer == "yes"


def test_quote_rule_rejects_an_empty_span():
    assert apply_quote_rule(Verdict("yes", 0.9, "  ", "x"), TURN).answer == "unsure"


def test_quote_rule_leaves_no_and_unsure_alone():
    assert apply_quote_rule(Verdict("no", 0.8, "", "x"), TURN).answer == "no"
    assert apply_quote_rule(Verdict("unsure", None, "", "x"), TURN).answer == "unsure"


def test_parse_answer_accepts_fenced_json():
    v = parse_answer('```json\n{"answer": "yes", "p": 0.7, "span": "clone"}\n```', "v")
    assert (v.answer, v.p, v.span, v.verifier) == ("yes", 0.7, "clone", "v")


def test_parse_answer_malformed_is_unsure():
    for raw in ["not json", '{"answer": "maybe"}', "[]", '{"answer": "yes", "p": "high", "span": 3}']:
        v = parse_answer(raw, "v")
        assert v.answer == "unsure" and v.reason


def test_brief_contains_turn_verbatim_and_definition():
    brief = build_brief(ANTI, TURN)
    assert TURN in brief and ANTI.definition in brief
    assert '"answer"' in brief and '"span"' in brief and "exactly" in brief


def test_headless_command_and_flags():
    seen = {}

    def runner(argv, **kwargs):
        seen["argv"], seen["input"], seen["timeout"] = argv, kwargs.get("input"), kwargs.get("timeout")
        return FakeCompleted(envelope('{"answer": "yes", "p": 0.9, "span": "a clone of someone"}'))

    v = HeadlessClaude(runner=runner).verify(ANTI, TURN)
    assert seen["argv"] == ["claude", "-p", "--model", "haiku", "--tools", "", "--no-session-persistence",
                            "--output-format", "json"]
    assert TURN in seen["input"] and seen["timeout"] == 60.0
    assert (v.answer, v.verifier) == ("yes", "headless-claude")


def test_headless_failure_modes_are_unsure():
    def fail_exit(argv, **kw):
        return FakeCompleted("", returncode=1)

    def not_json(argv, **kw):
        return FakeCompleted("not json")

    def times_out(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 60)

    def auth_error(argv, **kw):
        return FakeCompleted(envelope("Invalid API key · Please run /login", is_error=True))

    def missing(argv, **kw):
        raise FileNotFoundError("claude")

    for runner in (fail_exit, not_json, times_out, auth_error, missing):
        v = HeadlessClaude(runner=runner).verify(ANTI, TURN)
        assert v.answer == "unsure" and v.reason, runner.__name__


def test_ollama_request_shape():
    seen = {}

    def opener(request, timeout):
        seen["url"], seen["body"], seen["timeout"] = request.full_url, json.loads(request.data), timeout
        reply = {"response": '{"answer": "no", "p": 0.6, "span": ""}'}
        return io.BytesIO(json.dumps(reply).encode())

    v = OllamaVerifier("tev1", "http://model-host:11434", opener=opener).verify(ANTI, TURN)
    assert seen["url"] == "http://model-host:11434/api/generate"
    assert seen["body"]["model"] == "tev1" and seen["body"]["format"] == "json" and seen["body"]["stream"] is False
    assert seen["timeout"] == 20.0
    assert (v.answer, v.verifier) == ("no", "ollama:tev1")


def test_ollama_unreachable_is_unsure():
    def down(request, timeout):
        raise urllib.error.URLError("connection refused")

    def slow(request, timeout):
        raise TimeoutError("timed out")

    for opener in (down, slow):
        assert OllamaVerifier("tev1", "http://h:1", opener=opener).verify(ANTI, TURN).answer == "unsure"


def test_answer_file_verifier_is_labelled_and_quote_checked():
    v = AnswerFileVerifier({"anti_goal": {"answer": "yes", "p": 0.8, "span": "not in the turn"}}, "subagent")
    out = v.verify(ANTI, TURN)
    assert out.verifier == "subagent"
    assert AnswerFileVerifier({}, "session-model").verify(ANTI, TURN).answer == "unsure"


def test_select_verifiers_order():
    env = {"SPEC_READY_DECIDER": "ollama:tev1", "OLLAMA_HOST": "http://h:11434"}
    names = [v.name for v in select_verifiers(env, which=lambda c: "/bin/claude")]
    assert names == ["headless-claude", "ollama:tev1"]
    assert select_verifiers({}, which=lambda c: None) == []
    assert [v.name for v in select_verifiers({"SPEC_READY_DECIDER": "ollama:tev1"}, which=lambda c: None)] == []
    # No claude CLI but a local model configured: the local model is still independent of the agent.
    assert [v.name for v in select_verifiers(env, which=lambda c: None)] == ["ollama:tev1"]


def test_combine_disagreement_is_unsure():
    yes = Verdict("yes", 0.9, "s", "a")
    no = Verdict("no", 0.7, "", "b")
    assert combine([yes, no]).answer == "unsure" and "disagree" in combine([yes, no]).reason
    assert combine([yes, Verdict("yes", 0.6, "s", "b")]).p == 0.6
    assert combine([no, Verdict("unsure", None, "", "c")]).answer == "no"
    assert combine([]).answer == "unsure"
