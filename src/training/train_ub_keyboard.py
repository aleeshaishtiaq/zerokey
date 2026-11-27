"""Shortcut for ``python -m src.training.train_ub --modality keyboard``."""

from src.training.train_ub import evaluate_user, main, run  # noqa: F401

if __name__ == "__main__":
    main(modality="keyboard")
