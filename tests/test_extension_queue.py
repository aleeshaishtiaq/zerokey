"""Windows that cannot be sent are saved and sent later, only for the same user."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HARNESS = Path(__file__).with_name("background_harness.js")
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


@pytest.fixture(scope="module")
def result():
    output = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True, check=True)
    return json.loads(output.stdout)


def test_failed_windows_are_saved_and_flagged(result):
    assert result["first_sent"] == ["t1"]
    assert result["queued"] == ["t2", "t3"]
    assert result["failed_message_mentions_saved"] is True
    assert result["badge_after_failure"] == "!"


def test_saved_windows_are_sent_in_order_after_the_same_user_signs_in(result):
    assert result["sent_after_same_user"] == ["t1", "t2", "t3"]
    assert result["badge_after_sign_in"] == ""


def test_saved_windows_are_never_sent_for_another_user(result):
    assert "t4" not in result["sent_after_other_user"]
    assert result["queue_after_other_user"] == 0


def test_rejected_windows_are_not_saved_and_sign_out_clears_the_queue(result):
    assert result["queue_after_422"] == 0
    assert result["queue_before_logout"] == 1
    assert result["queue_after_logout"] == 0
