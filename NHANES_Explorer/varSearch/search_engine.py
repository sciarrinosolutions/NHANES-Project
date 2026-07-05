"""
search_engine.py
================
Builds a TF-IDF index over the NHANES codebook artifact CSV and exposes
a single search() function.

The index is built once at Django startup (lazy-loaded on first call) and
cached in memory for the lifetime of the process.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)

# ── Stop words to suppress from TF-IDF (extend as needed) ────────────────────
STOP_WORDS = [
    'the', 'a', 'an', 'and', 'or', 'of', 'in', 'to', 'for', 'is', 'are',
    'was', 'were', 'this', 'that', 'with', 'from', 'at', 'by', 'as', 'on',
    'be', 'it', 'its', 'not', 'no', 'do', 'did', 'sp', 'have', 'has',
]


def _build_search_text(row: pd.Series) -> str:
    """
    Concatenate all searchable text fields for a variable into one document.
    Fields are weighted by repetition: column_name and sas_label appear
    multiple times so they rank higher in TF-IDF scoring.
    """
    parts = []

    col  = str(row.get('column_name', '') or '')
    sas  = str(row.get('sas_label',   '') or '')
    desc = str(row.get('description', '') or '')
    comp = str(row.get('component',   '') or '')
    file = str(row.get('data_file',   '') or '')
    hr   = str(row.get('human_readable', '') or '')

    # Value labels -- extract just the label text, not the numeric codes
    vl_text = ''
    try:
        vl = json.loads(row.get('value_labels', '{}') or '{}')
        vl_text = ' '.join(vl.values())
    except Exception:
        pass

    # Boost column_name and sas_label by repeating them
    parts += [col] * 4
    parts += [sas] * 3
    parts += [hr]  * 2
    parts += [desc, comp, file, vl_text]

    return ' '.join(p for p in parts if p and p != 'nan')


@lru_cache(maxsize=1)
def _get_index():
    """
    Build and cache the TF-IDF index.
    Returns (df, vectorizer, tfidf_matrix).
    Called once; result is cached for the process lifetime.
    """
    from django.conf import settings

    artifact_path = Path(settings.NHANES_ARTIFACT_PATH)
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"NHANES artifact CSV not found at: {artifact_path}\n"
            f"Update NHANES_ARTIFACT_PATH in settings.py."
        )

    log.info("Loading NHANES artifact from %s", artifact_path)
    df = pd.read_csv(artifact_path, dtype=str).fillna('')
    log.info("Loaded %d variables. Building TF-IDF index...", len(df))

    corpus = df.apply(_build_search_text, axis=1).tolist()

    vectorizer = TfidfVectorizer(
        analyzer     = 'word',
        ngram_range  = (1, 2),       # unigrams + bigrams
        min_df       = 1,
        sublinear_tf = True,         # dampen very high term frequencies
        stop_words   = STOP_WORDS,
    )
    matrix = vectorizer.fit_transform(corpus)

    log.info("TF-IDF index built: %d variables, %d features",
             matrix.shape[0], matrix.shape[1])
    return df, vectorizer, matrix


def search(query: str, top_n: int = 30) -> list[dict]:
    """
    Search the NHANES artifact for variables related to the query.

    Scoring strategy:
      1. TF-IDF cosine similarity  (primary signal)
      2. Fuzzy partial match on column_name and sas_label  (secondary boost)

    Returns a list of dicts (up to top_n), sorted by combined score desc.
    Each dict contains all artifact columns plus 'score' and 'tfidf_score'.
    """
    if not query or not query.strip():
        return []

    query = query.strip()
    df, vectorizer, matrix = _get_index()

    # ── TF-IDF similarity ─────────────────────────────────────────────────────
    q_vec      = vectorizer.transform([query])
    cos_scores = cosine_similarity(q_vec, matrix).flatten()

    # ── Fuzzy boost on column_name and sas_label ──────────────────────────────
    query_lower = query.lower()
    fuzzy_scores = np.array([
        max(
            fuzz.partial_ratio(query_lower, str(row['column_name']).lower()),
            fuzz.partial_ratio(query_lower, str(row['sas_label']).lower()),
            fuzz.partial_ratio(query_lower, str(row['human_readable']).lower()),
        ) / 100.0
        for _, row in df.iterrows()
    ])

    # Combined score: 70% TF-IDF + 30% fuzzy
    combined = (0.70 * cos_scores) + (0.30 * fuzzy_scores)

    # ── Filter and rank ───────────────────────────────────────────────────────
    # Only return results with a meaningful combined score
    threshold    = 0.05
    top_indices  = np.where(combined >= threshold)[0]
    top_indices  = top_indices[np.argsort(combined[top_indices])[::-1]][:top_n]

    results = []
    for idx in top_indices:
        row = df.iloc[idx].to_dict()
        row['score']       = round(float(combined[idx]),    4)
        row['tfidf_score'] = round(float(cos_scores[idx]),  4)
        results.append(row)

    return results


def get_variable(column_name: str) -> dict | None:
    """
    Return a single variable's full record by column_name, or None if not found.
    """
    df, _, _ = _get_index()
    matches = df[df['column_name'] == column_name]
    if matches.empty:
        return None
    row = matches.iloc[0].to_dict()

    # Parse JSON fields for template consumption
    for field in ('value_labels', 'sentinel_values'):
        try:
            row[field] = json.loads(row.get(field, '{}') or '{}')
        except Exception:
            row[field] = {}

    return row
