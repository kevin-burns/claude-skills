"""Tiny record codec — fixture for the coherence-checker behavioral eval.

Per SPEC.md, encode/decode MUST round-trip EXACTLY: decode(encode(fields)) == fields,
including a trailing empty field. case_fold() is a separate helper whose contract IS to
lowercase (the precision control).
"""


def encode(fields):
    """Serialize a list of string fields into one newline-delimited blob."""
    return "\n".join(fields) + "\n"


def decode(blob):
    """Parse a newline-delimited blob back into a list of fields."""
    return blob.rstrip("\n").split("\n")  # drops a trailing empty field -> not an exact inverse


def case_fold(tag):
    """Lowercase a tag. Case-insensitivity IS this function's contract (control)."""
    return tag.lower()
