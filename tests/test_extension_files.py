"""Every place that injects the content script must load the same files."""

import ast
import json
import re
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[1] / "extension"


def test_hosted_portal_registration_loads_the_same_files_as_the_manifest():
    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    manifest_files = [entry["js"] for entry in manifest["content_scripts"]]
    background = (EXTENSION / "background.js").read_text(encoding="utf-8")
    match = re.search(r"registerContentScripts\(\[\s*\{.*?js:\s*(\[[^\]]*\])", background, re.S)
    registered = ast.literal_eval(match.group(1))

    assert all(files == registered for files in manifest_files)
    assert registered.index("features.js") < registered.index("content.js")
    for name in registered:
        assert (EXTENSION / name).is_file()
