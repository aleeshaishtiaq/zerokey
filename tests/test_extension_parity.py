"""The extension (content.js + features.js) and the training pipeline must give
the same feature values for the same input events."""

import json
import math
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from src.data_pipeline.prepare_training_windows import KeyboardWindow, MouseWindow

HARNESS = Path(__file__).with_name("extension_harness.js")
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def mouse_events(seed):
    rng = random.Random(seed)
    events, x, y, t = [], 400.0, 300.0, 0.0
    for _ in range(40):  # strokes, separated by short or long pauses
        t += rng.choice([150, 450, 900, 2_600])
        for _ in range(rng.randint(2, 25)):
            t += rng.uniform(6, 20)
            x += rng.uniform(-30, 30)
            y += rng.uniform(-30, 30)
            events.append({"type": "move", "x": round(x, 2), "y": round(y, 2), "t": round(t, 3)})
        if rng.random() < 0.5:
            t += rng.uniform(50, 1_200)
            events.append({"type": "click", "t": round(t, 3)})
        if rng.random() < 0.1:
            t += 100
            events.append({"type": "right", "t": round(t, 3)})
    return events


def key_events(seed):
    rng = random.Random(seed)
    events, t = [], 0.0
    codes = ["KeyA", "KeyS", "KeyD", "Space", "Backspace", "KeyE"]
    for _ in range(80):
        code = rng.choice(codes)
        t += rng.uniform(40, 700)
        events.append({"type": "down", "code": code, "t": round(t, 3)})
        up = t + rng.uniform(30, 200)
        if rng.random() < 0.2:  # overlap: next key goes down before this one is released
            other = rng.choice([c for c in codes if c != code])
            events.append({"type": "down", "code": other, "t": round(t + 20, 3)})
            events.append({"type": "up", "code": other, "t": round(up + 10, 3)})
        events.append({"type": "up", "code": code, "t": round(up, 3)})
        t = max(t, up)
    events.sort(key=lambda event: event["t"])
    return events


def run_extension(events):
    result = subprocess.run(["node", str(HARNESS)], input=json.dumps(events),
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def run_pipeline(events):
    mouse, keyboard = MouseWindow(), KeyboardWindow()
    for event in events:
        if event["type"] == "move":
            mouse.move(event["x"], event["y"], event["t"])
        elif event["type"] == "click":
            mouse.click(event["t"])
        elif event["type"] == "right":
            mouse.right_click()
        elif event["type"] == "down":
            keyboard.key_down(event["code"], event["t"])
        elif event["type"] == "up":
            keyboard.key_up(event["code"], event["t"])
    return mouse.features(), keyboard.features()


def assert_same(python_values, extension_values):
    compared = 0
    for name, expected in python_values.items():
        if name not in extension_values:
            continue
        actual = extension_values[name]
        if expected is None:
            assert actual is None, name
        else:
            assert actual is not None and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9), (
                name, expected, actual)
        compared += 1
    return compared


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_mouse_features_match(seed):
    events = mouse_events(seed)
    payload = run_extension(events)
    python_mouse, _ = run_pipeline(events)

    assert assert_same(python_mouse, payload["mouse_features"]) >= 25
    assert payload["mouse_features"]["stroke_count"] > 0


@pytest.mark.parametrize("seed", [1, 2])
def test_keyboard_features_match(seed):
    events = key_events(seed)
    payload = run_extension(events)
    _, python_keyboard = run_pipeline(events)

    assert assert_same(python_keyboard, payload["keyboard_features"]) >= 16
    assert payload["keyboard_features"]["backspace_rate"] > 0
