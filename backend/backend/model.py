from typing import List, Dict
import numpy as np
import os
import json

MODEL_PATH = os.path.join(os.path.dirname(__file__), "album_model.json")

def extract_features(albums: List[Dict]):
    rows = []
    now = np.datetime64('now')
    for alb in albums:
        popularity = float(alb.get('popularity') or 0.0)
        release_date = alb.get('release_date') or '1970-01-01'
        try:
            year = int(str(release_date).split('-')[0])
            release = np.datetime64(f"{year}-01-01")
            age_days = float((now - release).astype('timedelta64[D]') / np.timedelta64(1, 'D'))
        except Exception:
            age_days = 36525.0
        total_tracks = float(alb.get('total_tracks') or 0.0)
        rows.append([popularity, age_days, total_tracks])
    return np.array(rows, dtype=float)

def train_model(albums: List[Dict], labels: List[float]):
    X = extract_features(albums)
    y = np.array(labels, dtype=float)
    # simple linear regression using normal equation with intercept
    X_design = np.hstack([np.ones((X.shape[0], 1)), X])
    try:
        coef = np.linalg.lstsq(X_design, y, rcond=None)[0]
    except Exception:
        coef = np.zeros(X_design.shape[1])
    model = {'coef': coef.tolist()}
    with open(MODEL_PATH, 'w', encoding='utf8') as f:
        json.dump(model, f)
    return model

def load_model():
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, 'r', encoding='utf8') as f:
            return json.load(f)
    return None

def score_albums(albums: List[Dict], model=None):
    X = extract_features(albums)
    if model is None:
        # heuristic
        scores = []
        for row in X:
            pop = row[0] / 100.0
            recency = max(0.0, 1.0 - row[1] / 3650.0)
            score = 0.7 * pop + 0.3 * recency
            scores.append(round(float(score * 100), 2))
        return scores
    coef = np.array(model.get('coef', []), dtype=float)
    X_design = np.hstack([np.ones((X.shape[0], 1)), X])
    preds = X_design.dot(coef)
    minp, maxp = preds.min(), preds.max()
    if maxp - minp < 1e-6:
        return [round(float(p * 100), 2) for p in preds]
    return [round(float((p - minp) / (maxp - minp) * 100), 2) for p in preds]

