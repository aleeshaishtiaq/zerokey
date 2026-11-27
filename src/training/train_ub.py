"""Train and evaluate per-user models on the UB dataset, one modality at a time.

Usage (from the repo root):
    python -m src.training.train_ub --modality keyboard
    python -m src.training.train_ub --modality mouse
    python -m src.training.train_ub --modality mouse --feature-sets mouse27 \
        --min-strokes 2 --decision-windows 4
    python -m src.training.train_ub --modality keyboard --users 10 --models ocsvm

Rules (AGENTS.md > "Model training"):
- each user's model is fitted on that user's ``train`` windows only;
- the threshold is chosen on ``calibration`` (point where FAR = FRR);
- FAR / FRR at that threshold, EER and AUC are reported on ``test`` only;
- impostors are the other UB users of the same split and modality.
UB subjects without mouse windows (021, 049, 127) are simply not in the mouse
files, so they get a keyboard model only.

Options:
- ``--min-strokes N`` (mouse): use only windows with ``stroke_count >= N``, in
  every split. Coverage = share of test windows kept.
- ``--decision-windows K``: one decision = mean score of K consecutive windows
  of the same session (K = 4 is one minute). Sessions shorter than K give no
  decision. Applied the same way to calibration and test.
"""

import argparse
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from src.training.data import DEFAULT_DATA_DIR, FEATURE_SETS, SPLITS, load_split_with_sessions
from src.training.metrics import auc, eer, far_frr
from src.training.models import DEFAULT_PARAMS, MODEL_NAMES, UserModel, autoencoder_layers

DEFAULT_OUTPUT_ROOT = Path("data") / "processed" / "models"
METRIC_COLUMNS = ("calibration_eer", "test_far", "test_frr", "test_eer", "test_auc")

log = logging.getLogger("train_ub")


def decision_scores(scores, users, sessions, windows=1):
    """Mean of ``windows`` consecutive scores inside each (user, session) run.

    Rows must be in time order. Returns (scores, users) of the decisions.
    """
    scores = np.asarray(scores, dtype=float)
    if windows <= 1:
        return scores, np.asarray(users)
    out_scores, out_users = [], []
    start = 0
    for end in range(1, len(scores) + 1):
        if end == len(scores) or users[end] != users[start] or sessions[end] != sessions[start]:
            run = scores[start:end]
            if run.size >= windows:
                kernel = np.ones(windows) / windows
                means = np.convolve(run, kernel, mode="valid")
                out_scores.append(means)
                out_users.extend([users[start]] * means.size)
            start = end
    if not out_scores:
        return np.array([]), np.array([])
    return np.concatenate(out_scores), np.array(out_users)


def evaluate_user(model_name, user, splits, random_state=42, decision_windows=1):
    """Fit one user's model and return its metrics row."""
    train_x, train_users = splits["train"][:2]
    model = UserModel(model_name, random_state=random_state).fit(train_x[train_users == user])

    row = {"user_id": user, "train_windows": int(np.sum(train_users == user))}
    scores = {}
    for split in ("calibration", "test"):
        x, users = splits[split][:2]
        sessions = splits[split][2] if len(splits[split]) > 2 else np.zeros(len(users))
        decided, decided_users = decision_scores(
            model.score(x), users, sessions, decision_windows,
        )
        scores[split] = (decided[decided_users == user], decided[decided_users != user])
        row[f"{split}_genuine"] = int(scores[split][0].size)
        row[f"{split}_impostor"] = int(scores[split][1].size)
        if not scores[split][0].size or not scores[split][1].size:
            return None

    row["calibration_eer"], row["threshold"] = eer(*scores["calibration"])
    row["test_far"], row["test_frr"] = far_frr(*scores["test"], row["threshold"])
    row["test_eer"], _ = eer(*scores["test"])
    row["test_auc"] = auc(*scores["test"])
    return row


def summarize(rows):
    summary = {"users": len(rows)}
    for column in METRIC_COLUMNS:
        values = np.array([row[column] for row in rows], dtype=float)
        summary[f"{column}_mean"] = float(values.mean())
        summary[f"{column}_std"] = float(values.std())
    return summary


def load_splits(data_dir, modality, features, max_users=None, min_strokes=None):
    """Return (users, splits, coverage); splits[split] = (X, user_ids, session_ids)."""
    loaded = {
        split: load_split_with_sessions(data_dir, "ub", modality, split, features, min_strokes)
        for split in SPLITS
    }
    # Only users with train windows get a model; other splits keep the same users.
    users = sorted(set(loaded["train"][1]))
    if max_users:
        users = users[:max_users]
    splits = {}
    for split, (x, u, sessions, _total) in loaded.items():
        keep = np.isin(u, users)
        splits[split] = (x[keep], u[keep], sessions[keep])
    total_test = loaded["test"][3]
    coverage = len(loaded["test"][1]) / total_test if total_test else 0.0
    return users, splits, coverage


def run(data_dir, output_dir, models, feature_sets, max_users=None, random_state=42,
        modality="keyboard", min_strokes=None, decision_windows=1):
    output_dir.mkdir(parents=True, exist_ok=True)
    per_user_rows = []
    summaries = []

    for set_name in feature_sets:
        features = FEATURE_SETS[modality][set_name]
        users, splits, coverage = load_splits(
            data_dir, modality, features, max_users, min_strokes,
        )
        for model_name in models:
            started = time.time()
            rows = []
            for user in users:
                row = evaluate_user(model_name, user, splits, random_state, decision_windows)
                if row is None:
                    continue
                row.update({"model": model_name, "feature_set": set_name})
                rows.append(row)
            summary = summarize(rows)
            summary.update({
                "model": model_name,
                "feature_set": set_name,
                "min_strokes": min_strokes or 0,
                "decision_windows": decision_windows,
                "test_window_coverage": coverage,
                "users_without_decisions": len(users) - len(rows),
                "seconds": round(time.time() - started, 1),
            })
            log.info(
                "%-11s %-8s users=%d test EER=%.4f AUC=%.4f FAR=%.4f FRR=%.4f "
                "coverage=%.2f (%.0fs)",
                model_name, set_name, summary["users"], summary["test_eer_mean"],
                summary["test_auc_mean"], summary["test_far_mean"],
                summary["test_frr_mean"], coverage, summary["seconds"],
            )
            per_user_rows.extend(rows)
            summaries.append(summary)

    write_outputs(output_dir, per_user_rows, summaries, models, feature_sets, random_state,
                  modality, min_strokes, decision_windows)
    return summaries


def write_outputs(output_dir, per_user_rows, summaries, models, feature_sets, random_state,
                  modality="keyboard", min_strokes=None, decision_windows=1):
    columns = [
        "model", "feature_set", "user_id", "train_windows",
        "calibration_genuine", "calibration_impostor", "test_genuine", "test_impostor",
        "threshold", *METRIC_COLUMNS,
    ]
    with open(output_dir / "per_user_metrics.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(per_user_rows)

    with open(output_dir / "summary.json", "w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)

    sets = FEATURE_SETS[modality]
    best = min(summaries, key=lambda item: item["test_eer_mean"])
    config = {
        "source": "ub",
        "modality": modality,
        "models": list(models),
        "feature_sets": {name: list(sets[name]) for name in feature_sets},
        "params": {name: DEFAULT_PARAMS[name] for name in models},
        "autoencoder_layers": {
            name: list(autoencoder_layers(len(sets[name]))) for name in feature_sets
        },
        "scaling": "StandardScaler per user and model, fitted on that user's train windows",
        "threshold": "per user, where FAR = FRR on calibration",
        "impostors": "other UB users of the same split and modality",
        "min_strokes": min_strokes or 0,
        "decision_windows": decision_windows,
        "random_state": random_state,
        "best_by_test_eer": {"model": best["model"], "feature_set": best["feature_set"]},
    }
    with open(output_dir / "config.json", "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def parse_args(argv=None, modality=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    if modality is None:
        parser.add_argument("--modality", choices=sorted(FEATURE_SETS), required=True)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--models", nargs="+", choices=MODEL_NAMES, default=list(MODEL_NAMES))
    parser.add_argument(
        "--feature-sets", nargs="+", default=None,
        help="default: every set of the modality (keyboard: abs10 all15 abs10_v2 all21; "
             "mouse: mouse5 mouse15 mouse27)",
    )
    parser.add_argument("--users", type=int, default=None, help="only the first N users")
    parser.add_argument("--min-strokes", type=int, default=None,
                        help="mouse only: keep windows with stroke_count >= N")
    parser.add_argument("--decision-windows", type=int, default=1,
                        help="mean score of K consecutive windows per decision (4 = 1 minute)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    if modality is not None:
        args.modality = modality
    known = FEATURE_SETS[args.modality]
    args.feature_sets = args.feature_sets or list(known)
    unknown = [name for name in args.feature_sets if name not in known]
    if unknown:
        parser.error(f"unknown {args.modality} feature set(s): {', '.join(unknown)}")
    if args.min_strokes and args.modality != "mouse":
        parser.error("--min-strokes only applies to --modality mouse")
    if args.decision_windows < 1:
        parser.error("--decision-windows must be 1 or more")
    return args


def main(argv=None, modality=None):
    args = parse_args(argv, modality)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or DEFAULT_OUTPUT_ROOT / f"ub_{args.modality}" / stamp
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(output_dir / "run.log", encoding="utf-8"),
        ],
    )
    log.info(
        "modality: %s  min strokes: %s  decision windows: %d  data: %s  output: %s",
        args.modality, args.min_strokes or 0, args.decision_windows, args.data_dir, output_dir,
    )
    run(args.data_dir, output_dir, args.models, args.feature_sets, args.users, args.seed,
        args.modality, args.min_strokes, args.decision_windows)
    log.info("done: results in %s", output_dir)


if __name__ == "__main__":
    main()
