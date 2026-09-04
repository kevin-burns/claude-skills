"""Tests for the pluggable backend registry and the network backends' request
building.

MUST NOT import any ASR library -- these run in an environment with none of
mlx-whisper, faster-whisper or nemo_toolkit installed, and that absence is
part of what several tests here verify (`load()` on an uninstalled backend).
`tslib.backends.groq` and `tslib.backends.openai` are safe to import
directly: they are stdlib-`urllib` only and contain no ASR import at all,
lazy or otherwise.

THE MOST IMPORTANT TEST IN THIS FILE is `test_auto_never_returns_network`:
this skill exists because a competing tool uploaded audio without saying so,
and the one invariant that must never regress is that 'auto' cannot reach a
network backend under any platform this module can be asked to pretend to
be.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

# Import via a sys.path insert of scripts/, per the project's test convention
# (see ruff.toml's per-file-ignores for **/tests/* -- E402 is expected here).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tslib import backends  # noqa: E402
from tslib.backends import _openai_compatible as oai  # noqa: E402
from tslib.backends import groq, openai  # noqa: E402

# ---------------------------------------------------------------------------
# resolve(): platform detection and the auto -> local-only invariant
# ---------------------------------------------------------------------------


def test_auto_on_darwin_arm64_is_mlx_whisper():
    assert backends.resolve("auto", system="darwin", machine="arm64").name == "mlx-whisper"


def test_auto_on_linux_x86_64_is_faster_whisper():
    assert backends.resolve("auto", system="linux", machine="x86_64").name == "faster-whisper"


def test_auto_on_darwin_x86_64_is_faster_whisper():
    # Intel Mac: MLX does not run there, so auto must fall back, not fail.
    assert backends.resolve("auto", system="darwin", machine="x86_64").name == "faster-whisper"


# Every platform combination worth naming. The point of this list is
# breadth, not that any individual entry is exotic.
PLATFORM_COMBOS = [
    ("darwin", "arm64"),
    ("darwin", "aarch64"),
    ("darwin", "x86_64"),
    ("linux", "x86_64"),
    ("linux", "aarch64"),
    ("linux", "armv7l"),
    ("win32", "AMD64"),
    ("win32", "ARM64"),
    ("cygwin", "x86_64"),
    ("freebsd13", "amd64"),
    ("darwin", "i386"),
    ("linux", "i686"),
]


@pytest.mark.parametrize(("system", "machine"), PLATFORM_COMBOS)
def test_auto_never_returns_network(system, machine):
    """THE IMPORTANT ONE. 'auto' must never yield a network backend -- not
    as a default, not as a fallback -- on any platform.
    """
    info = backends.resolve("auto", system=system, machine=machine)
    assert info.kind == "local"


def test_auto_defaults_to_real_platform_when_unoverridden():
    # No system/machine passed: falls through to sys.platform / platform.machine().
    # Still must never be network, whatever this test happens to run on.
    assert backends.resolve("auto").kind == "local"


def test_explicit_network_backend_still_resolves():
    """Auto never reaches the network, but a caller naming it explicitly is
    a different thing entirely -- that is the opt-in the whole design hinges
    on, and it must still work.
    """
    info = backends.resolve("groq")
    assert info.kind == "network"
    assert info.name == "groq"


def test_resolve_unknown_backend_lists_valid_names():
    with pytest.raises(backends.UnknownBackend) as exc_info:
        backends.resolve("nonsense")
    message = str(exc_info.value)
    for valid_name in backends.REGISTRY:
        assert valid_name in message


# ---------------------------------------------------------------------------
# load() and dependency reporting
# ---------------------------------------------------------------------------


def test_load_missing_dependency_names_pip_spec():
    # parakeet's dependency (nemo_toolkit) is the least likely of any backend
    # to be present in a test environment, so it is the safest one to assert
    # "not installed" against.
    info = backends.REGISTRY["parakeet"]
    with pytest.raises(backends.MissingDependency) as exc_info:
        backends.load(info)
    message = str(exc_info.value)
    assert info.pip_spec in message
    assert "--backend parakeet" in message


# ---------------------------------------------------------------------------
# Registry contents
# ---------------------------------------------------------------------------


def test_only_parakeet_lacks_whisper_metrics():
    assert backends.REGISTRY["parakeet"].has_whisper_metrics is False
    for name, info in backends.REGISTRY.items():
        if name == "parakeet":
            continue
        assert info.has_whisper_metrics is True, f"{name} should have has_whisper_metrics=True"


def test_network_backends_have_no_pip_spec():
    # groq and openai are stdlib-urllib only -- nothing to install, so
    # nothing for MissingDependency to ever report for them.
    assert backends.REGISTRY["groq"].pip_spec is None
    assert backends.REGISTRY["openai"].pip_spec is None


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def test_estimate_cost_groq_whisper_large_v3():
    assert backends.estimate_cost("groq", "whisper-large-v3", 3600) == pytest.approx(0.111)


def test_estimate_cost_unknown_model_is_none():
    assert backends.estimate_cost("groq", "some-future-model", 3600) is None


def test_estimate_cost_local_backend_is_none():
    assert backends.estimate_cost("mlx-whisper", "large-v3", 3600) is None


# ---------------------------------------------------------------------------
# Network backends: the API key never leaves the environment or leaks into
# an error. No real network call is made anywhere in this file.
# ---------------------------------------------------------------------------


def test_groq_missing_key_raises_and_names_the_variable(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"not real audio, just needs to exist as a file")

    with pytest.raises(groq.GroqError) as exc_info:
        groq.transcribe(wav)

    message = str(exc_info.value)
    assert "GROQ_API_KEY" in message


def test_openai_missing_key_raises_and_names_the_variable(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"not real audio, just needs to exist as a file")

    with pytest.raises(openai.OpenAIError) as exc_info:
        openai.transcribe(wav)

    message = str(exc_info.value)
    assert "OPENAI_API_KEY" in message


def test_groq_decoy_key_reaches_headers_but_never_an_error(monkeypatch, tmp_path):
    """A DECOY key (never a real one) must reach the Authorization header -- that
    is how auth works -- and must be reachable from nowhere else.

    No network stub any more: `build_request` returns the prepared headers, so
    this asserts on data instead of on a mocked transport. The transport is
    `HTTPSConnection`, which has no scheme to subvert.
    """
    monkeypatch.setenv("GROQ_API_KEY", "decoy-not-a-real-key")
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"not real audio, just needs to exist as a file")

    prepared = oai.build_request(
        groq.PROVIDER, wav, model=groq.DEFAULT_MODEL, language="en", prompt=None,
        key=oai.api_key(groq.PROVIDER),
    )
    assert prepared.headers["Authorization"] == "Bearer decoy-not-a-real-key"
    assert prepared.host == "api.groq.com"

    # An unreachable host exercises the error path the key must never enter.
    unreachable = oai.Provider(
        name="groq", label="Groq", endpoint="https://127.0.0.1:9/v1/audio/transcriptions",
        env_var="GROQ_API_KEY", default_model="m", error=groq.GroqError,
    )
    with pytest.raises(groq.GroqError) as exc_info:
        oai.send(unreachable, oai.build_request(
            unreachable, wav, model="m", language=None, prompt=None, key="decoy-not-a-real-key"), timeout=2.0)
    err_text = f"{exc_info.value!s} {exc_info.value!r}"
    assert "decoy-not-a-real-key" not in err_text

def test_openai_decoy_key_reaches_headers_but_never_an_error(monkeypatch, tmp_path):
    """A DECOY key (never a real one) must reach the Authorization header -- that
    is how auth works -- and must be reachable from nowhere else.

    No network stub any more: `build_request` returns the prepared headers, so
    this asserts on data instead of on a mocked transport. The transport is
    `HTTPSConnection`, which has no scheme to subvert.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "decoy-not-a-real-key")
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"not real audio, just needs to exist as a file")

    prepared = oai.build_request(
        openai.PROVIDER, wav, model=openai.DEFAULT_MODEL, language="en", prompt=None,
        key=oai.api_key(openai.PROVIDER),
    )
    assert prepared.headers["Authorization"] == "Bearer decoy-not-a-real-key"
    assert prepared.host == "api.openai.com"

    # An unreachable host exercises the error path the key must never enter.
    unreachable = oai.Provider(
        name="openai", label="Openai", endpoint="https://127.0.0.1:9/v1/audio/transcriptions",
        env_var="OPENAI_API_KEY", default_model="m", error=openai.OpenAIError,
    )
    with pytest.raises(openai.OpenAIError) as exc_info:
        oai.send(unreachable, oai.build_request(
            unreachable, wav, model="m", language=None, prompt=None, key="decoy-not-a-real-key"), timeout=2.0)
    err_text = f"{exc_info.value!s} {exc_info.value!r}"
    assert "decoy-not-a-real-key" not in err_text

def test_groq_oversized_file_names_shrink_command(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "decoy-not-a-real-key")
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"x" * (groq.MAX_UPLOAD_BYTES + 1))

    with pytest.raises(groq.GroqError) as exc_info:
        groq.transcribe(wav)

    message = str(exc_info.value)
    assert "ffmpeg" in message
    assert "flac" in message
    assert "decoy-not-a-real-key" not in message


# --------------------------------------------------------------------- scheme guard
#
# Bandit flags urlopen (B310) because a non-https URL turns an API client into a
# local file reader. Every endpoint here is a module constant today, so these
# tests are about the change that has not happened yet: a configurable endpoint
# for a self-hosted or Azure-style host.


def test_a_file_url_endpoint_cannot_even_be_expressed(tmp_path):
    """The B310 failure mode, removed rather than guarded.

    The transport is `http.client.HTTPSConnection`, which speaks no other
    scheme, so `file://` cannot reach it. `Provider.host` refuses the config
    outright, so the failure is at construction rather than at send time.
    """
    secret = tmp_path / "secret.txt"
    secret.write_text("not audio")
    hostile = oai.Provider(
        name="hostile", label="Hostile", endpoint=f"file://{secret}",
        env_var="HOSTILE_KEY", default_model="m", error=RuntimeError,
    )
    with pytest.raises(ValueError, match="must be https"):
        _ = hostile.host


def test_a_plain_http_endpoint_is_refused_so_the_key_is_never_sent_in_clear():
    insecure = oai.Provider(
        name="insecure", label="Insecure", endpoint="http://api.example.com/v1/audio/transcriptions",
        env_var="INSECURE_KEY", default_model="m", error=RuntimeError,
    )
    with pytest.raises(ValueError, match="must be https"):
        _ = insecure.host


def test_the_transport_module_never_calls_urlopen():
    """A regression guard on the fix itself: reintroducing urlopen reintroduces
    the scheme problem, and bandit's B310 with it.

    Checked on the AST, not with a substring search -- `send()`'s docstring names
    urlopen in order to explain why it is not used, and a grep-shaped test would
    fail on the explanation. Imports and call targets are what matter.
    """
    tree = ast.parse(Path(oai.__file__).read_text())

    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "urllib.request" not in imported, "urllib.request is back; so is the file:// path"
    assert "http.client" in imported

    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "urlopen" not in called


def test_the_shipped_providers_are_all_https():
    for module in (groq, openai):
        assert module.PROVIDER.endpoint.startswith("https://"), module.PROVIDER.name
