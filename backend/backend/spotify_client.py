import os
import time
from dotenv import load_dotenv
import httpx

# Explicitly load the backend/.env file so environment is correct regardless of cwd
here = os.path.dirname(__file__)
env_path = os.path.join(here, '..', '.env')
load_dotenv(env_path)

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

_token_cache = {"token": None, "expires_at": 0}

async def get_token() -> str:
    now = int(time.time())
    if _token_cache["token"] and _token_cache["expires_at"] > now + 30:
        return _token_cache["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "client_credentials",
                "client_id": SPOTIFY_CLIENT_ID,
                "client_secret": SPOTIFY_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + int(expires_in)
        return token

async def fetch_artist_albums(artist_id: str):
    token = await get_token()
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album&market=US&limit=50"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        resp.raise_for_status()
        return resp.json()

async def fetch_album_tracks(album_id: str):
    token = await get_token()
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks?market=US&limit=50"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        resp.raise_for_status()
        return resp.json()
