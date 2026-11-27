"""One-class models: One-Class SVM, Isolation Forest and an MLP autoencoder.

Every model is wrapped so that ``score`` returns an anomaly score where higher
means "less like the enrolled user". Each model has its own scaler, fitted on
the user's ``train`` windows only.
"""

import warnings

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

MODEL_NAMES = ("ocsvm", "iforest", "autoencoder")

DEFAULT_PARAMS = {
    "ocsvm": {"kernel": "rbf", "nu": 0.1, "gamma": "scale"},
    "iforest": {"n_estimators": 200, "max_samples": "auto", "contamination": "auto"},
    "autoencoder": {
        "activation": "tanh",
        "alpha": 1e-3,
        "learning_rate_init": 1e-3,
        "max_iter": 2000,
    },
}


def autoencoder_layers(n_features):
    """Encoder-bottleneck-decoder sizes, e.g. 10 -> (6, 3, 6), 15 -> (10, 5, 10)."""
    hidden = max(2, (2 * n_features) // 3)
    bottleneck = max(2, n_features // 3)
    return (hidden, bottleneck, hidden)


class UserModel:
    """A one-class model for one user and one modality."""

    def __init__(self, name, random_state=42, params=None):
        if name not in MODEL_NAMES:
            raise ValueError(f"unknown model: {name}")
        self.name = name
        self.random_state = random_state
        self.params = dict(DEFAULT_PARAMS[name], **(params or {}))
        self.scaler = StandardScaler()
        self.estimator = None

    def fit(self, train):
        train = np.asarray(train, dtype=float)
        scaled = self.scaler.fit_transform(train)
        if self.name == "ocsvm":
            self.estimator = OneClassSVM(**self.params)
            self.estimator.fit(scaled)
        elif self.name == "iforest":
            self.estimator = IsolationForest(random_state=self.random_state, **self.params)
            self.estimator.fit(scaled)
        else:
            self.estimator = MLPRegressor(
                hidden_layer_sizes=autoencoder_layers(train.shape[1]),
                random_state=self.random_state,
                **self.params,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConvergenceWarning)
                self.estimator.fit(scaled, scaled)
        return self

    def score(self, windows):
        if self.estimator is None:
            raise RuntimeError("fit the model before scoring")
        scaled = self.scaler.transform(np.asarray(windows, dtype=float))
        if self.name == "ocsvm":
            return -self.estimator.decision_function(scaled)
        if self.name == "iforest":
            return -self.estimator.score_samples(scaled)
        reconstructed = self.estimator.predict(scaled)
        return np.mean((scaled - reconstructed) ** 2, axis=1)
