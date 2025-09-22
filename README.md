I love Spotify, but I hate it when I want to listen to a song and can't remember the name — I only remember the cover image, so I end up doom-scrolling through album after album to find it.

![Spotify logo](https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_with_text.svg)

## What this project is
A small web app that helps you find and rank an artist's albums using a tiny machine-learned model. The frontend (Vite + React) lists albums and shows a model score under each album card, so you can see what other people think about it. The backend (FastAPI) talks to Spotify, computes scores with a simple trainable linear model (NumPy), and exposes a /recommend API that returns ranked albums and scores.

## High-level architecture
- Frontend
  - `src/App.jsx` — search box, fetches artist albums, asks the backend for model scores, and displays album cards (image, title, release date, link, model score).
  - Built with Vite + React and React-Bootstrap.
- Backend
  - `backend/backend/main.py` — FastAPI app exposing `/recommend` and `/train`.
  - `backend/backend/spotify_client.py` — Spotify client-credentials helpers and album fetch.
  - `backend/backend/model.py` — feature extraction, training, scoring (pure NumPy linear model + heuristic fallback).
  - Model persistence: `backend/backend/album_model.json` (created by training).
- Data flow
  1. Frontend obtains artist id (or the backend does) → obtains album list.
  2. Frontend calls backend `/recommend?artist_id=...`.
  3. Backend fetches albums, computes scores (using the trained model if available; otherwise uses a heuristic), and returns `ranked` albums with `score`.
  4. Frontend merges scores into album objects and displays "Model score: X.X — higher is better".

## How the score is determined (concise, accurate)
- Features extracted per album:
  - `popularity` — Spotify album popularity (0–100). If missing, treated as 0.
  - `age_days` — age computed from the album release year (days since year-01-01 of release).
  - `total_tracks` — number of tracks on the album.
- If a trained model is available (`album_model.json`):
  - The backend builds X_design = [1, popularity, age_days, total_tracks] for each album.
  - It computes raw predictions: pred = X_design · coef (linear regression coefficients).
  - Predictions are min/max-normalized across the albums in the current request:
    score = (pred - min(preds)) / (max(preds) - min(preds)) * 100
    (If preds have essentially zero range, it returns pred * 100 as a fallback.)
  - Final scores are rounded to 2 decimal places in the backend.
- If no model file exists (heuristic fallback):
  - popularity is scaled: pop_norm = popularity / 100
  - recency factor: recency = max(0, 1 - age_days/3650)  (decay over ~10 years)
  - heuristic score (0..1): score_raw = 0.7 * pop_norm + 0.3 * recency
  - scaled to 0..100 and rounded to 2 decimals.
- The frontend displays a single decimal (e.g., 27.8) with the human hint "higher is better". The backend values are merged into `album.score` before display.

## Important details / edge cases
- Popularity often missing in the artist-albums response; missing popularity becomes 0, which can bias scores toward newer albums or those with more tracks.
- Age uses only the year for release_date parsing, so exact day/month is ignored (coarse age).
- Scores are normalized per-request (min-max across the albums returned for the artist), so values are relative to the set of albums returned, not an absolute global scale.
- If predicted values are nearly identical (no variance), the code avoids divide-by-zero and scales differently (returns pred * 100).
- Final numeric rounding happens on the backend (2 decimals) and frontend shows 1 decimal.

## How you can improve score quality (quick suggestions)
- Fetch full album objects (GET /albums/{id}) to get accurate `popularity` and other fields.
- Add more features: average track popularity, audio features (energy/valence), editorial metadata.
- Collect labeled training data (user likes/dislikes) and retrain the linear model with real labels.
- Change weighting or model family (e.g., regularized regression, tree models) if data grows.

## API
- GET /recommend?artist_id={spotify_artist_id}
  - Response: JSON with `recommended` and `ranked`. `ranked` is an array of entries shaped as:
    - either `{ album: {...}, score: 12.34 }` or (older shape) `{ id: '...', score: 12.34 }`
  - Each album object contains fields returned by Spotify: `id`, `name`, `release_date`, `images`, `external_urls`, etc.
- POST /train
  - Body: `{ albums: [...], labels: [...] }` (matching lengths)
  - Trains a linear model and writes `album_model.json`.

## Setup (Windows / PowerShell)
1. Frontend env (keep secrets out of git)
   - Create `.env` in the repo root or set environment variables for Vite:
     ```
     VITE_CLIENT_ID=your_spotify_client_id
     VITE_CLIENT_SECRET=your_spotify_client_secret
     VITE_BACKEND_URL=http://127.0.0.1:8000
     ```
   - Do NOT commit real secrets to the repo.
2. Backend env
   - Create `backend/.env` with:
     ```
     SPOTIFY_CLIENT_ID=your_spotify_client_id
     SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
     ```
3. Install backend deps and start backend (PowerShell):
   ```powershell
   cd backend
   .venv\Scripts\Activate.ps1   # if you use the provided venv, or create one
   pip install -r requirements.txt
   uvicorn backend.main:app --reload
   ```
4. Start frontend:
   ```powershell
   # from repo root
   npm install
   npm run dev
   ```
5. Open the Vite URL (usually http://localhost:5173) and search for an artist.

## Troubleshooting tips
- If `npm` fails on PowerShell due to ExecutionPolicy: run npm using `npm.cmd` or set policy:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
- If backend returns CORS errors: backend already sets CORS to allow origins=["*"] in the current code; ensure the backend server is running and reachable by the frontend.
- If scores don't appear:
  - Confirm backend is running and that the frontend can call `VITE_BACKEND_URL/recommend`.
  - Check browser devtools Network tab to inspect the `/recommend` request and response shape.
- If popularity is consistently 0:
  - The artist albums endpoint does not include album `popularity` always. Improving scoring requires fetching full album objects (`GET /albums/{id}`) to obtain popularity and track-level metadata.

## Security notes
- Never commit `SPOTIFY_CLIENT_SECRET` or `VITE_CLIENT_SECRET` to a public repo.
- Prefer doing all Spotify-authenticated calls on the backend so secrets remain server-side. If you want, I can remove client-credentials usage from the frontend and add a backend artist-search endpoint.

## Development notes and next improvements
- Improve features: fetch full album objects to get `popularity`, compute average track popularity, pull audio features (danceability/energy/valence), use them as model inputs.
- Better model: gather labeled user data, use regularized regression or a small tree model (if wheels available) for better performance.
- UI improvements: color-coded score badges, sort options, and a small “why this” tooltip that explains the main contributors (popularity vs. recency).
- Persistence: use a DB or simple file store for training data and votes.

## Where to look in the code
- Frontend: `src/App.jsx`
- Backend API: `backend/backend/main.py`
- Spotify helper: `backend/backend/spotify_client.py`
- Model logic: `backend/backend/model.py`
- Environment examples: `backend/.env` (not committed, keep secrets)

---

If you want I can:
- Paste this as a `README.md` file in the repo (I can create it).
- Add a short “how the UI displays the score” screenshot/notes or color-coding logic.
- Replace client-side Spotify auth and move artist lookup to the backend (recommended for security).
# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh
