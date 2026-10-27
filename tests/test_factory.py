"""The fixture factory: what a full project holds."""
import json
from pathlib import Path

import common
import factory


def test_factory(project):
    refs = {}
    for sid, count in factory.SET_SIZES.items():
        files = sorted(p for p in (project / "input" / "refs" / sid).iterdir())
        assert len(files) == count
        refs[sid] = [f"input/refs/{sid}/{p.name}" for p in files]
    for name in ("rfp.md", "brand-logo.png", "product.png"):
        assert (project / "input" / name).is_file()
    assert (project / "brief" / "brand" / "logo.png").read_bytes() == \
        (project / "input" / "brand-logo.png").read_bytes()

    hashes = set()
    for key in ("set-1/A", "set-1/B", "set-2/A", "set-2/B"):
        renders = project / "concepts" / key / "renders"
        for stem in ("hero-v1", "hero-v2"):
            assert (renders / f"{stem}.png").is_file()
            hashes.add(common.sha256_file(str(renders / f"{stem}.png")))
        info = json.loads((renders / "hero-v1.json").read_text(encoding="utf-8"))
        assert info["schema"] == "sidecar/2" and info["mode"] == "hero" and info["tool"] == "render.py"
        assert (info["set"], info["concept"]) == tuple(key.split("/"))
        assert info["inputs"] and all(i["role"] == "ref" for i in info["inputs"])
        assert info["outputs"] == {"hero-v1.png": common.sha256_file(str(renders / "hero-v1.png"))}
        prompt = (project / "concepts" / key / "prompts" / "hero.txt").read_text(encoding="utf-8").strip()
        assert (renders / "hero-v1.prompt.txt").read_text(encoding="utf-8") == prompt
        assert info["prompt_sha256"] == common.sha256_file(str(renders / "hero-v1.prompt.txt"))

    assert len(factory.SEND_LOG) == 4
    assert all(entry["fields"]["n"] == 2 for entry in factory.SEND_LOG)
    own = [refs["set-1"], refs["set-1"], refs["set-2"], refs["set-2"]]
    for entry, expected in zip(factory.SEND_LOG, own):
        assert sorted(Path(p).as_posix() for p in entry["images"]) == expected

    assert len(hashes) == 8
    ref_hashes = {common.sha256_file(str(project / p)) for files in refs.values() for p in files}
    assert not hashes & ref_hashes
    assert not (project / "brief" / "selection.json").exists()
