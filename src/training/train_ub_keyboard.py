"""Train and evaluate per-user keyboard models on the UB dataset.

Usage (from the repo root):
    python -m src.training.train_ub_keyboard
    python -m src.training.train_ub_keyboard --users 10 --models ocsvm iforest

Rules (AGENTS.md > "Model training"):
- each user's model is fitted on that user's ``train`` windows only;
- the threshold is chosen on ``calibration`` (point where FAR = FRR);
- FAR / FRR at that threshold, EER and AUC are reported on ``test`` only;
- impostors are the other UB users of the same split.
"""

import argparse
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from src.training.data import DEFAULT_DATA_DIR, KEYBOARD_FEATURE_SETS, SPLITS, load_split
from src.training.metrics import auc, eer, far_frr
from src.training.models import DEFAULT_PARAMS, MODEL_NAMES, UserModel, autoencoder_layers

DEFAULT_OUTPUT_DIR = Path("data") / "processed" / "models" / "ub_keyboard"
METRIC_COLUMNS = ("calibration_eer", "test_far", "test_frr", "test_eer", "test_auc")

log = logging.getLogger("train_ub_keyboard")


def evaluate_user(model_name, user, splits, random_state=42):
    """Fit one user's model and return its metrics row."""
    train_x, train_users = splits["train"]
    model = UserModel(model_name, random_state=random_state).fit(train_x[train_users == user])

    row = {"user_id": user, "train_windows": int(np.sum(train_users == user))}
    scores = {}
    for split in ("calibration", "test"):
        x, users = splits[split]
        split_scores = model.score(x)
        scores[split] = (split_scores[users == user], split_scores[users != user])
        row[f"{split}_genuine"] = int(scores[split][0].size)
        row[f"{split}_impostor"] = int(scores[split][1].size)

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


def run(data_dir, output_dir, models, feature_sets, max_users=None, random_state=42):
    output_dir.mkdir(parents=True, exist_ok=True)
    per_user_rows = []
    summaries = []

    for set_name in feature_sets:
        features = KEYBOARD_FEATURE_SETS[set_name]
        splits = {
            split: load_split(data_dir, "ub", "keyboard", split, features)
            for split in SPLITS
        }
        users = sorted(set(splits["train"][1]))
        if max_users:
            users = users[:max_users]
            splits = {
                split: (x[np.isin(u, users)], u[np.isin(u, users)])
                for split, (x, u) in splits.items()
            }
        for model_name in models:
            started = time.time()
            rows = []
            for user in users:
                row = evaluate_user(model_name, user, splits, random_state)
                row.update({"model": model_name, "feature_set": set_name})
                rows.append(row)
            summary = summarize(rows)
            summary.update({
                "model": model_name,
                "feature_set": set_name,
                "seconds": round(time.time() - started, 1),
            })
            log.info(
                "%-11s %-5s users=%d test EER=%.4f AUC=%.4f FAR=%.4f FRR=%.4f (%.0fs)",
                model_name, set_name, summary["users"], summary["test_eer_mean"],
                summary["test_auc_mean"], summary["test_far_mean"],
                summary["test_frr_mean"], summary["seconds"],
            )
            per_user_rows.extend(rows)
            summaries.append(summary)

    write_outputs(output_dir, per_user_rows, summaries, models, feature_sets, random_state)
    return summaries


def write_outputs(output_dir, per_user_rows, summaries, models, feature_sets, random_state):
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

    best = min(summaries, key=lambda item: item["test_eer_mean"])
    config = {
        "source": "ub",
        "modality": "keyboard",
        "models": list(models),
        "feature_sets": {name: list(KEYBOARD_FEATURE_SETS[name]) for name in feature_sets},
        "params": {name: DEFAULT_PARAMS[name] for name in models},
        "autoencoder_layers": {
            name: list(autoencoder_layers(len(KEYBOARD_FEATURE_SETS[name])))
            for name in feature_sets
        },
        "scaling": "StandardScaler per user and model, fitted on that user's train windows",
        "threshold": "per user, where FAR = FRR on calibration",
        "impostors": "other UB users of the same split",
        "random_state": random_state,
        "best_by_test_eer": {"model": best["model"], "feature_set": best["feature_set"]},
    }
    with open(output_dir / "config.json", "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--models", nargs="+", choices=MODEL_NAMES, default=list(MODEL_NAMES))
    parser.add_argument(
        "--feature-sets", nargs="+", choices=sorted(KEYBOARD_FEATURE_SETS),
        default=["abs10", "all15"],
    )
    parser.add_argument("--users", type=int, default=None, help="only the first N users")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(output_dir / "run.log", encoding="utf-8"),
        ],
    )
    log.info("data: %s  output: %s", args.data_dir, output_dir)
    run(args.data_dir, output_dir, args.models, args.feature_sets, args.users, args.seed)
    log.info("done: results in %s", output_dir)


if __name__ == "__main__":
    main()
