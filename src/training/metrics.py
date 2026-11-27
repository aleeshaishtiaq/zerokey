"""Verification metrics on anomaly scores.

Convention: a higher score means "less like the enrolled user". A window is
accepted when ``score <= threshold``.
FAR = share of impostor windows accepted, FRR = share of genuine windows rejected.
"""

import numpy as np


def far_frr(genuine, impostor, threshold):
    genuine = np.asarray(genuine, dtype=float)
    impostor = np.asarray(impostor, dtype=float)
    far = float(np.mean(impostor <= threshold)) if impostor.size else 0.0
    frr = float(np.mean(genuine > threshold)) if genuine.size else 0.0
    return far, frr


def eer(genuine, impostor):
    """Return (eer, threshold) where FAR and FRR are closest."""
    genuine = np.sort(np.asarray(genuine, dtype=float))
    impostor = np.sort(np.asarray(impostor, dtype=float))
    if not genuine.size or not impostor.size:
        raise ValueError("eer needs genuine and impostor scores")
    thresholds = np.unique(np.concatenate([genuine, impostor]))
    far = np.searchsorted(impostor, thresholds, side="right") / impostor.size
    frr = 1.0 - np.searchsorted(genuine, thresholds, side="right") / genuine.size
    best = int(np.argmin(np.abs(far - frr)))
    return float((far[best] + frr[best]) / 2.0), float(thresholds[best])


def auc(genuine, impostor):
    """Probability that an impostor window scores higher than a genuine one."""
    genuine = np.asarray(genuine, dtype=float)
    impostor = np.asarray(impostor, dtype=float)
    if not genuine.size or not impostor.size:
        raise ValueError("auc needs genuine and impostor scores")
    sorted_genuine = np.sort(genuine)
    below = np.searchsorted(sorted_genuine, impostor, side="left")
    ties = np.searchsorted(sorted_genuine, impostor, side="right") - below
    return float((below.sum() + 0.5 * ties.sum()) / (genuine.size * impostor.size))
