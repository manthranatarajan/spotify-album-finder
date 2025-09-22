from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .spotify_client import fetch_artist_albums
from .model import load_model, score_albums, train_model
import asyncio

app = FastAPI(title="Album Recommender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/recommend")
async def recommend(artist_id: str = Query(..., description="Spotify artist id")):
    try:
        data = await fetch_artist_albums(artist_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    items = data.get("items", [])
    # fetch albums' full metadata asynchronously (Spotify's artist albums already include basic fields)
    albums = []
    for a in items:
        albums.append({
            "id": a.get("id"),
            "name": a.get("name"),
            "release_date": a.get("release_date"),
            "total_tracks": a.get("total_tracks"),
            "images": a.get("images"),
            "external_urls": a.get("external_urls"),
            # popularity field not present here; it's available in album object if full album object requested
            "popularity": a.get("popularity", 0),
        })

    model = load_model()
    scores = score_albums(albums, model=model)
    ranked = sorted(
        [dict(album=alb, score=s) for alb, s in zip(albums, scores)],
        key=lambda x: x["score"],
        reverse=True,
    )

    recommended = ranked[0] if ranked else None
    return {"recommended": recommended, "ranked": ranked}


@app.post("/train")
async def train(payload: dict):
    # payload must contain 'albums' (list) and 'labels' (list of numbers)
    albums = payload.get("albums")
    labels = payload.get("labels")
    if not albums or not labels or len(albums) != len(labels):
        raise HTTPException(status_code=400, detail="albums and labels required and must match length")

    model = train_model(albums, labels)
    return {"status": "trained"}
