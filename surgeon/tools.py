import os
import requests
from pathlib import Path


def search_maven_central(query: str) -> list:
    resp = requests.get(
        "https://search.maven.org/solrsearch/select",
        params={"q": query, "rows": 3, "wt": "json"},
        timeout=10,
    )
    resp.raise_for_status()
    docs = resp.json().get("response", {}).get("docs", [])
    return [
        {
            "groupId": d.get("g"),
            "artifactId": d.get("a"),
            "version": d.get("v"),
            "lastPublished": d.get("timestamp"),
        }
        for d in docs
    ]


def read_source_file(path: str, line_range: list) -> str:
    repo_root = Path(os.environ.get("REPO_ROOT", ".")).resolve()
    target = (repo_root / path).resolve()
    if not str(target).startswith(str(repo_root)):
        raise ValueError(f"Path escapes repo root: {path}")
    if target.is_symlink():
        raise ValueError(f"Symlinks not allowed: {path}")
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    start, end = int(line_range[0]), int(line_range[1])
    end = min(end, start + 199)
    lines = target.read_text(errors="replace").splitlines()
    return "\n".join(lines[start - 1 : end])
