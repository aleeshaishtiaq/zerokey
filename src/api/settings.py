"""Load the repository ``.env`` file for local runs.

On Vercel the variables come from the project settings and ``.env`` is not
deployed, so this is a no-op there. Variables that are already set in the
environment always win, so nothing configured on the server is overridden.
"""

import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path = REPOSITORY_ROOT / ".env") -> None:
    if "pytest" in sys.modules or os.getenv("ZEROKEY_SKIP_DOTENV"):
        return
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if name and name not in os.environ:
            os.environ[name] = value


def resolve_repository_path(value: str, default: Path) -> Path:
    """Resolve a relative path against the repository root, not the CWD."""
    if not value.strip():
        return default
    path = Path(value.strip())
    return path if path.is_absolute() else REPOSITORY_ROOT / path


load_dotenv()
