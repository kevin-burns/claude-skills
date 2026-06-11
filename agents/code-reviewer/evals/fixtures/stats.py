"""Small stats helpers — fixture for the code-reviewer behavioral eval.

Contains ONE planted correctness bug (median, even-length branch) and one
deliberately-correct function (clamp) as a precision control: the reviewer
should flag the former and NOT invent a blocking issue in the latter.
"""


def median(nums):
    """Return the median of a non-empty list of numbers."""
    s = sorted(nums)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid] + s[mid + 1]) / 2  # planted bug: should be s[mid - 1]
    return s[mid]


def clamp(value, low, high):
    """Clamp value into the inclusive range [low, high]. (Correct — control.)"""
    return max(low, min(value, high))
