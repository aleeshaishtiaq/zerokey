"""Per-user one-class models and verification metrics."""

import json

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("sklearn")

from src.training.data import (  # noqa: E402
    KEYBOARD_FEATURE_SETS, MOUSE_FEATURE_SETS, MOUSE_FEATURES, load_split,
)
from src.training.metrics import auc, eer, far_frr  # noqa: E402
from src.training.models import MODEL_NAMES, UserModel, autoencoder_layers  # noqa: E402
from src.training.train_ub import decision_scores, evaluate_user, parse_args, run  # noqa: E402


def test_metrics_on_perfectly_separated_scores():
    genuine = [0.1, 0.2, 0.3]
    impostor = [0.7, 0.8, 0.9]

    assert far_frr(genuine, impostor, 0.5) == (0.0, 0.0)
    assert eer(genuine, impostor)[0] == 0.0
    assert auc(genuine, impostor) == 1.0


def test_metrics_on_identical_scores():
    scores = [0.5, 0.5, 0.5, 0.5]

    assert auc(scores, scores) == 0.5
    assert far_frr(scores, scores, 0.5) == (1.0, 0.0)


def test_eer_threshold_balances_far_and_frr():
    genuine = [0.1, 0.2, 0.3, 0.6]
    impostor = [0.4, 0.7, 0.8, 0.9]

    rate, threshold = eer(genuine, impostor)
    far, frr = far_frr(genuine, impostor, threshold)

    assert rate == pytest.approx(0.25)
    assert far == pytest.approx(frr)


def test_autoencoder_has_a_bottleneck():
    assert autoencoder_layers(10) == (6, 3, 6)
    assert autoencoder_layers(15) == (10, 5, 10)


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_models_score_impostors_higher(name):
    rng = np.random.default_rng(0)
    genuine = rng.normal(0.0, 1.0, size=(120, 4))
    impostor = rng.normal(6.0, 1.0, size=(60, 4))

    model = UserModel(name).fit(genuine[:80])
    scores_genuine = model.score(genuine[80:])
    scores_impostor = model.score(impostor)

    assert scores_genuine.shape == (40,)
    assert auc(scores_genuine, scores_impostor) > 0.95


def test_unknown_model_is_rejected():
    with pytest.raises(ValueError):
        UserModel("knn")


def write_split(directory, split, users, rng, modality="keyboard"):
    features = KEYBOARD_FEATURE_SETS["all15"] if modality == "keyboard" else MOUSE_FEATURES
    path = directory / f"ub_{modality}_{split}_clean.jsonl"
    with open(path, "w", encoding="utf-8") as handle:
        for index, user in enumerate(users):
            for _ in range(30):
                values = rng.normal(index * 5.0, 1.0, size=len(features))
                row = {
                    "user_id": user,
                    f"{modality}_features": dict(zip(features, values.tolist())),
                }
                handle.write(json.dumps(row) + "\n")


def test_run_uses_other_users_as_impostors_and_writes_outputs(tmp_path):
    rng = np.random.default_rng(1)
    users = ["001", "002", "003"]
    for split in ("train", "calibration", "test"):
        write_split(tmp_path, split, users, rng)
    output = tmp_path / "out"

    summaries = run(tmp_path, output, ["iforest"], ["abs10"])

    assert summaries[0]["users"] == 3
    assert summaries[0]["test_auc_mean"] > 0.95
    assert (output / "per_user_metrics.csv").exists()
    assert (output / "summary.json").exists()
    config = json.loads((output / "config.json").read_text(encoding="utf-8"))
    assert config["best_by_test_eer"]["model"] == "iforest"

    splits = {
        split: load_split(tmp_path, "ub", "keyboard", split, KEYBOARD_FEATURE_SETS["abs10"])
        for split in ("train", "calibration", "test")
    }
    row = evaluate_user("ocsvm", "001", splits)
    assert row["test_genuine"] == 30
    assert row["test_impostor"] == 60


def test_mouse_run_only_models_users_with_train_windows(tmp_path):
    rng = np.random.default_rng(2)
    write_split(tmp_path, "train", ["001", "002", "003"], rng, "mouse")
    for split in ("calibration", "test"):
        # "004" has no train windows (like UB 021, 049, 127): no model, not an impostor.
        write_split(tmp_path, split, ["001", "002", "003", "004"], rng, "mouse")
    output = tmp_path / "out"

    summaries = run(tmp_path, output, ["ocsvm"], ["mouse5"], modality="mouse")

    assert summaries[0]["users"] == 3
    config = json.loads((output / "config.json").read_text(encoding="utf-8"))
    assert config["modality"] == "mouse"
    assert config["autoencoder_layers"]["mouse5"] == [3, 2, 3]
    lines = (output / "per_user_metrics.csv").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    assert all(",60," in line for line in lines[1:])  # 2 other users x 30 impostor windows


def test_feature_sets_default_to_the_modality():
    assert parse_args(["--modality", "mouse"]).feature_sets == ["mouse5", "mouse15", "mouse27"]
    assert parse_args(["--modality", "keyboard"]).feature_sets == [
        "abs10", "all15", "abs10_v2", "all21",
    ]
    with pytest.raises(SystemExit):
        parse_args(["--modality", "mouse", "--feature-sets", "abs10"])


def test_feature_set_v2_keeps_every_v1_feature():
    from src.training.data import KEYBOARD_V2_FEATURES, MOUSE_V2_FEATURES

    assert KEYBOARD_FEATURE_SETS["abs10_v2"][:10] == KEYBOARD_FEATURE_SETS["abs10"]
    assert KEYBOARD_FEATURE_SETS["all21"][:15] == KEYBOARD_FEATURE_SETS["all15"]
    assert KEYBOARD_FEATURE_SETS["all21"][15:] == KEYBOARD_V2_FEATURES
    assert MOUSE_FEATURE_SETS["mouse15"] == MOUSE_FEATURES + MOUSE_V2_FEATURES
    assert len(set(KEYBOARD_FEATURE_SETS["all21"])) == 21


def test_decision_scores_average_inside_each_session_only():
    scores = [1, 2, 3, 4, 10, 20, 5, 5]
    users = np.array(["a", "a", "a", "a", "a", "a", "b", "b"])
    sessions = np.array(["s1", "s1", "s1", "s1", "s2", "s2", "s3", "s3"])

    decided, decided_users = decision_scores(scores, users, sessions, windows=2)

    assert decided.tolist() == [1.5, 2.5, 3.5, 15.0, 5.0]
    assert decided_users.tolist() == ["a", "a", "a", "a", "b"]
    same, same_users = decision_scores(scores, users, sessions, windows=1)
    assert same.tolist() == [float(value) for value in scores]

    short, _ = decision_scores([1, 2], ["a", "a"], ["s1", "s1"], windows=3)
    assert short.size == 0


def write_stroke_split(directory, split, rng):
    path = directory / f"ub_mouse_{split}_clean.jsonl"
    with open(path, "w", encoding="utf-8") as handle:
        for index, user in enumerate(["001", "002", "003"]):
            for window in range(40):
                values = rng.normal(index * 5.0, 1.0, size=len(MOUSE_FEATURE_SETS["mouse27"]))
                features = dict(zip(MOUSE_FEATURE_SETS["mouse27"], values.tolist()))
                features["stroke_count"] = float(window % 4)  # 0, 1, 2, 3
                handle.write(json.dumps({
                    "user_id": user, "session_id": f"{user}{split}", "window_index": window,
                    "mouse_features": features,
                }) + "\n")


def test_min_strokes_and_decision_windows(tmp_path):
    rng = np.random.default_rng(3)
    for split in ("train", "calibration", "test"):
        write_stroke_split(tmp_path, split, rng)

    summaries = run(tmp_path, tmp_path / "out", ["iforest"], ["mouse27"], modality="mouse",
                    min_strokes=2, decision_windows=4)

    assert summaries[0]["users"] == 3
    assert summaries[0]["test_window_coverage"] == 0.5
    assert summaries[0]["decision_windows"] == 4
    lines = (tmp_path / "out" / "per_user_metrics.csv").read_text(encoding="utf-8").splitlines()
    # 20 kept windows per user and split -> 17 decisions of 4 windows.
    assert all(",17,34," in line for line in lines[1:])


def test_min_strokes_is_mouse_only():
    with pytest.raises(SystemExit):
        parse_args(["--modality", "keyboard", "--min-strokes", "2"])
