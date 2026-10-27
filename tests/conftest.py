"""Shared fixtures. tmp_path may be on another drive than the repo: never compute relpath between them."""
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "skills" / "booth-proposal" / "scripts"
for _p in (str(SCRIPTS), str(TESTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import factory  # noqa: E402
import gates  # noqa: E402
import render  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_send_log():
    factory.SEND_LOG.clear()
    yield
    factory.SEND_LOG.clear()


@pytest.fixture
def make_project(tmp_path):
    """make(**kw) builds tmp_path/proj<n> with factory.build_project and returns its Path."""
    counter = [0]

    def make(**kw):
        counter[0] += 1
        return factory.build_project(tmp_path / f"proj{counter[0]}", **kw)

    return make


@pytest.fixture
def project(make_project):
    return make_project()


@pytest.fixture
def run_gates(capsys):
    """run(root, *args) -> (exit code, stdout, stderr); --project is appended after the command."""
    def run(root, *args):
        capsys.readouterr()
        try:
            code = gates.main([*args, "--project", str(root)])
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
        out = capsys.readouterr()
        return code, out.out, out.err

    return run


@pytest.fixture
def has():
    """has(text, code, rule=None) -> the finding lines of text with that code (and message rule prefix)."""
    import re

    def find(text, code, rule=None):
        hits = []
        for line in text.splitlines():
            parts = line.split(None, 2)
            if len(parts) < 3 or parts[0] not in ("ERROR", "WARN", "PENDING") or parts[1] != code:
                continue
            if rule is None or re.search(rf"(^|: ){re.escape(rule)}:", parts[2]):
                hits.append(line)
        return hits

    return find


@pytest.fixture
def fake_send(monkeypatch):
    """Replaces render.send: records (url, fields, images) in fake_send.calls and answers with fields["n"] new
    1536x1024 PNGs (a new solid colour for each image). Sets OPENAI_API_KEY to sk-test-SECRET."""
    import base64

    def send(url, key, fields, images, image_field):
        send.calls.append((url, dict(fields), list(images)))
        data = [{"b64_json": base64.b64encode(factory.png_bytes(factory._next_rgb(), size=(1536, 1024))).decode("ascii")}
                for _ in range(int(fields["n"]))]
        return {"data": data, "usage": {"total_tokens": 1}}

    send.calls = []
    monkeypatch.setattr(render, "send", send)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-SECRET")
    return send
