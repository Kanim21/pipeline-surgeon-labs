import json
import os
import pytest
from pathlib import Path

from surgeon.llm import classify
from surgeon.redactor import redact

FIXTURES_DIR = Path(__file__).parent / "fixtures"
THRESHOLD = 0.6


def _fixture_pairs():
    pairs = []
    for log_file in sorted(FIXTURES_DIR.glob("*.log")):
        expected_file = log_file.with_suffix(".expected.json")
        if expected_file.exists():
            pairs.append((log_file, expected_file))
    return pairs


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
@pytest.mark.parametrize(
    "log_path,expected_path",
    _fixture_pairs(),
    ids=lambda p: p.stem,
)
def test_classification(log_path, expected_path):
    log_text = log_path.read_text(errors="replace")
    expected = json.loads(expected_path.read_text())

    diagnosis = classify(redact(log_text))

    assert diagnosis["failure_class"] == expected["failure_class"], (
        f"Expected failure_class={expected['failure_class']!r}, "
        f"got {diagnosis['failure_class']!r}"
    )
    assert diagnosis["confidence"] >= THRESHOLD, (
        f"Confidence {diagnosis['confidence']:.2f} below threshold {THRESHOLD}"
    )
    assert diagnosis.get("target_file") == expected["target_file"], (
        f"Expected target_file={expected['target_file']!r}, "
        f"got {diagnosis.get('target_file')!r}"
    )
    reasoning_lower = diagnosis["reasoning"].lower()
    for kw in expected["reasoning_keywords"]:
        assert kw.lower() in reasoning_lower, (
            f"Expected keyword {kw!r} not found in reasoning"
        )
