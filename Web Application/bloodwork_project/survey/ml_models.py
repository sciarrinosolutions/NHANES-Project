"""
Model loader for all five blood test models.

Each model is stored as a pkl bundle containing:
    features  - list of feature names in training column order
    scaler    - fitted StandardScaler
    imputer   - fitted KNNImputer
    model     - fitted LogisticRegression
    threshold - float, default 0.5
    label     - human-readable target label

Placeholder bundles are used when no pkl file exists for a given test.
Swap in real pkl files by placing them at ml/<test_key>_model.pkl.
"""

import pickle
import logging
import numpy as np
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

_bundles = {}


def _make_placeholder_bundle(test_key, features):
    """
    Returns a dummy bundle that always predicts ~50% probability.
    Used until real trained pkl files are supplied.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import KNNImputer

    n = len(features)
    X_dummy = np.random.randn(40, n)
    y_dummy = np.array([0, 1] * 20)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_dummy)

    imputer = KNNImputer(n_neighbors=3)
    X_imputed = imputer.fit_transform(X_scaled)

    model = LogisticRegression(random_state=42, max_iter=200)
    model.fit(X_imputed, y_dummy)
    # Zero out coefficients so all placeholder models return ~50%
    model.coef_[:] = 0.0
    model.intercept_[:] = 0.0

    return {
        'features': features,
        'scaler': scaler,
        'imputer': imputer,
        'model': model,
        'threshold': 0.5,
        'label': test_key,
        'is_placeholder': True,
    }


def get_bundle(test_key, features):
    """
    Returns the model bundle for a given test key.
    Loads from disk if the pkl exists; otherwise returns a placeholder.
    Results are cached in memory after the first load.
    """
    global _bundles
    if test_key in _bundles:
        return _bundles[test_key]

    pkl_path = Path(settings.ML_MODELS_DIR) / f"{test_key}_model.pkl"

    if pkl_path.exists():
        logger.info(f"Loading real model for {test_key} from {pkl_path}")
        with open(pkl_path, 'rb') as f:
            bundle = pickle.load(f)
        logger.info(f"Model for {test_key} loaded successfully.")
    else:
        logger.warning(
            f"No pkl found at {pkl_path}. Using placeholder model for {test_key}."
        )
        bundle = _make_placeholder_bundle(test_key, features)

    _bundles[test_key] = bundle
    return bundle


def clear_cache():
    """Call this after swapping in a new pkl file to force a reload."""
    global _bundles
    _bundles = {}
