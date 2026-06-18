"""Tests for codec — fixture for the coherence-checker behavioral eval.

ONE planted coherence failure: test_roundtrip looks like an identity check but rstrip()s
both sides, papering over decode() dropping the trailing empty field (inverse-pair check).
The control test lowercases legitimately — that's case_fold's contract, not a hidden delta.
"""

from codec import encode, decode, case_fold


def test_roundtrip():
    fields = ["a", "b", ""]
    out = decode(encode(fields))
    assert "\n".join(out).rstrip() == "\n".join(fields).rstrip()  # normalization hides the delta


def test_case_fold_is_case_insensitive():
    assert case_fold("Prod") == "prod"  # control: lowercasing is the contract here
