"""
Prediction engine.

Takes cleaned form data and a list of selected test keys.
For each test, extracts the relevant features, applies the pipeline,
and returns a structured result including feature contributions.
"""

import numpy as np
from .tests_config import TESTS, QUESTIONS
from .ml_models import get_bundle

import datetime


# ---------------------------------------------------------------------------
# Feature extraction helpers
# ---------------------------------------------------------------------------

def extract_features(cleaned_data, feature_keys):
    """
    Given cleaned form data (a dict), extract and compute the numeric value
    for each feature key required by a model.

    Returns a dict: {feature_key: numeric_value}
    """
    values = {}

    # Compute BMI once if height/weight fields are present
    bmi_value = None
    if 'height_ft' in cleaned_data and 'weight_lb' in cleaned_data:
        total_inches = float(cleaned_data['height_ft']) * 12 + float(cleaned_data.get('height_in', 0))
        weight = float(cleaned_data['weight_lb'])
        if total_inches > 0:
            bmi_value = (weight * 703) / (total_inches ** 2)

    # Compute race ethnicity dummies once
    race_eth_3 = None
    race_eth_4 = None
    if 'race_ethnicity' in cleaned_data:
        code = int(float(cleaned_data['race_ethnicity']))
        race_eth_3 = 1.0 if code == 3 else 0.0
        race_eth_4 = 1.0 if code == 4 else 0.0

    # Compute exam season from current month if not provided
    exam_season_value = None
    if 'exam_season' in cleaned_data:
        exam_season_value = float(cleaned_data['exam_season'])

    for key in feature_keys:
        if key == 'bmi':
            values[key] = bmi_value
        elif key == 'sedentary_time_per_day':
            # Convert hours (form input) to minutes (model expects minutes)
            if key in cleaned_data:
                values[key] = float(cleaned_data[key]) * 60
        elif key == 'map':
            # map is now a direct radio value (MAP midpoint), pass through as-is
            if key in cleaned_data:
                values[key] = float(cleaned_data[key])
        elif key == 'race_ethnicity':
            # race_ethnicity is a proxy; the actual model features are the two dummies
            # handled separately below — skip the raw key
            pass
        elif key == 'race_ethnicity_3.0':
            values[key] = race_eth_3
        elif key == 'race_ethnicity_4.0':
            values[key] = race_eth_4
        elif key == 'exam_season':
            values[key] = exam_season_value
        elif key in cleaned_data:
            values[key] = float(cleaned_data[key])

    return values


def run_prediction(test_key, test_features, cleaned_data):
    """
    Runs inference for a single test.

    Returns a dict with:
        test_key, label, full_label, recommend, prob_high, prob_normal,
        contributions (list of dicts with feature, label, value, direction, weight),
        is_placeholder
    """
    from .tests_config import TESTS

    test_meta = next(t for t in TESTS if t['key'] == test_key)

    # Resolve the actual model feature list, expanding race_ethnicity
    model_features = []
    for f in test_features:
        if f == 'race_ethnicity':
            model_features.extend(['race_ethnicity_3.0', 'race_ethnicity_4.0'])
        else:
            model_features.append(f)

    bundle = get_bundle(test_key, model_features)

    # Use the bundle's own feature order if available (real model)
    # Fall back to our derived list (placeholder)
    bundle_features = bundle.get('features', model_features)

    # Extract values in bundle feature order
    value_map = extract_features(cleaned_data, model_features)

    X_raw = np.array([
        value_map.get(f, np.nan) for f in bundle_features
    ]).reshape(1, -1)

    X_scaled  = bundle['scaler'].transform(X_raw)
    X_imputed = bundle['imputer'].transform(X_scaled)

    model = bundle['model']
    probs = model.predict_proba(X_imputed)[0]
    prob_high   = float(probs[1])
    prob_normal = float(probs[0])
    recommend   = prob_high >= bundle['threshold']

    # --- Feature contributions ---
    # contribution_i = coef_i * scaled_imputed_value_i
    # Positive = pushes toward high/abnormal, negative = pushes toward normal
    coefs = model.coef_[0]
    scaled_values = X_imputed[0]
    raw_contribs = coefs * scaled_values

    # Build contributions, merging race_ethnicity_3.0 and race_ethnicity_4.0
    # into a single entry by summing their contributions
    contrib_map = {}
    for i, feat in enumerate(bundle_features):
        display_key = feat
        if feat in ('race_ethnicity_3.0', 'race_ethnicity_4.0'):
            display_key = 'race_ethnicity'

        q_meta = QUESTIONS.get(display_key, {})
        feat_label = q_meta.get('label', feat.replace('_', ' ').title())
        contrib = float(raw_contribs[i])

        if display_key in contrib_map:
            # Sum contributions from both race/ethnicity dummy columns
            contrib_map[display_key]['contribution'] += contrib
        else:
            contrib_map[display_key] = {
                'feature':      display_key,
                'label':        feat_label,
                'contribution': contrib,
            }

    contributions = []
    for entry in contrib_map.values():
        contrib = entry['contribution']
        contributions.append({
            'feature':      entry['feature'],
            'label':        entry['label'],
            'contribution': contrib,
            'direction':    'risk' if contrib > 0 else 'protective',
        })

    # Sort by absolute contribution, strongest first
    contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
    top = contributions[:5]

    # Normalize bars so the largest absolute contribution = 100%
    # This makes relative sizes visible regardless of how small the raw values are
    max_abs = max((abs(c['contribution']) for c in top), default=1)
    if max_abs == 0:
        max_abs = 1
    for c in top:
        c['pct'] = round((abs(c['contribution']) / max_abs) * 100, 1)

    return {
        'test_key':      test_key,
        'label':         test_meta['label'],
        'full_label':    test_meta['full_label'],
        'description':   test_meta['description'],
        'recommend':     recommend,
        'prob_high':     round(prob_high * 100, 1),
        'prob_normal':   round(prob_normal * 100, 1),
        'contributions': top,
        'is_placeholder': bundle.get('is_placeholder', False),
    }


def run_all_predictions(selected_test_keys, cleaned_data):
    """
    Runs inference for every selected test and returns a list of result dicts.
    """
    results = []
    for test in TESTS:
        if test['key'] not in selected_test_keys:
            continue
        result = run_prediction(test['key'], test['features'], cleaned_data)
        results.append(result)
    return results
