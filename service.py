import json
import logging
from typing import List, Optional, Tuple
from asyncpg import Record
from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from settings import (
    COVERT_ART_ARCHIVE_BASE_URL,
    LAST_FM_API_KEY,
    MUSICBRAINZ_BASE_URL,
    THE_LAST_FM_BASE_URL,
)
from utils import make_api_request
from validation import AddMusicModel

logger = logging.getLogger(__name__)


async def add_music(request: Request, data: AddMusicModel):
    status, msg, validated_data = validate_music(data)
    if not status:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation error: {msg}",
        )
    query = """
        INSERT INTO events
        (title, recording_id, artist, artist_id, album, release_id, duration, playbackRate, bundle, elapsed, deviceName, is_valid, playcount) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 1)
        ON CONFLICT (title, artist, album)
        DO UPDATE SET 
        playbackRate = $8, bundle = $9, elapsed = $10, deviceName = $11, 
        playcount = events.playcount + 1, updated = now();
    """
    db_data = {
        "title": validated_data["title"],
        "recording_id": validated_data.get("recording_id"),
        "artist": validated_data.get("artist"),
        "artist_id": validated_data.get("artist_id"),
        "album": validated_data.get("album"),
        "release_id": validated_data.get("release_id"),
        "duration": validated_data.get("duration"),
        "playbackRate": validated_data.get("playbackRate"),
        "bundle": validated_data.get("bundle"),
        "elapsed": validated_data.get("elapsed"),
        "deviceName": validated_data.get("deviceName"),
        "is_valid": status,
    }
    
    try:
        await request.app.db.execute(query, *db_data.values())
    except Exception as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}",
        )
    return JSONResponse(content={"message": "Data saved successfully"}, status_code=200)


def validate_music(data: AddMusicModel):
    status, msg, resp = lookup_track_mb(data.title, data.artist, data.album or "")
    if status != "success":
        logger.error(f"Track lookup failed: {msg}")
        return False, "Track lookup failed", {}

    data_model = data.model_dump()
    data_model.update(resp)
    return True, "success", data_model


# Lookup Track from MusicBrainz
def lookup_track_mb(
    title: str, artist: str, album: Optional[str], retry: int = 4
) -> Tuple[str, dict]:
    if retry < 0:
        return False, "No results found after multiple attempts", {}
    base_url = f"{MUSICBRAINZ_BASE_URL}/ws/2/recording"
    query = f'recording:"{title}" AND artist:"{artist}"'
    if album:
        query += f' AND release:"{album}"'

    params = {"query": query, "fmt": "json", "limit": 1}

    status, reason, response = make_api_request(base_url, "GET", params=params)
    if not status:
        if reason.startswith("rate limit"):
            return lookup_track_lastfm(title, artist, retry=retry - 1)
        return False, "request failed", {}

    try:
        data = response.json()
        result = {}
        for recording in data.get("recordings", []):
            if recording.get("score", 0) == 100:
                result["recording_id"] = recording["id"]
                result["title"] = recording["title"]
                if recording.get("artist-credit"):
                    result["artist"] = recording["artist-credit"][0].get("name")
                    result["artist_id"] = (
                        recording["artist-credit"][0].get("artist", {}).get("id")
                    )
                if recording.get("releases"):
                    result["release_id"] = recording["releases"][0].get("id")
                    result["release_title"] = recording["releases"][0].get("title")
                    result["release_status"] = recording["releases"][0].get("status")
                return "success", result
        return False, "No results found", {}
    except json.JSONDecodeError:
        return False, "Invalid JSON response", {}
    return False, "No results found", {}


# Lookup Track from last.fm
def lookup_track_lastfm(title: str, artist: str, retry: int = 4) -> Tuple[str, dict]:
    if retry < 0:
        return False, "No results found after multiple attempts", {}
    base_url = f"{THE_LAST_FM_BASE_URL}/2.0"

    params = {
        "format": "json",
        "method": "track.getInfo",
        "apikey": LAST_FM_API_KEY,
        "artist": artist,
        "track": title,
    }

    status, reason, response = make_api_request(base_url, "GET", params=params)
    if not status:
        if reason.startswith("rate limit"):
            return lookup_track_mb(title, artist, retry=retry - 1)
        return False, "request failed", {}
    try:
        data = response.json()
        print(data)
        if data.get("track") is None:
            return False, "No results found", {}

        result = {}

        data = data.get("track", {})
        result["title"] = data.get("name")
        result["recording_id"] = data.get("mbid")
        result["artist"] = data.get("album", {}).get("artist")
        result["artist_id"] = data.get("artist", {}).get("mbid")
        result["album"] = data.get("album", {}).get("title")
        result["release_id"] = data.get("album", {}).get("mbid")
        result["duration"] = int(data.get("duration", 0))
        return True, "success", result

    except json.JSONDecodeError:
        return False, "Invalid JSON response", {}


def get_cover_art(request: Request, release_id: str):
    if not release_id:
        raise HTTPException(
            status_code=400,
            detail="Missing release_id",
        )
    base_url = f"{COVERT_ART_ARCHIVE_BASE_URL}/release/{release_id}"

    status, reason, response = make_api_request(base_url, "GET")
    if not status:
        return JSONResponse(
            content={"message": f"Failed to get cover art due to {reason}"},
            status_code=400,
        )

    try:
        data = response.json()
        if data.get("images") is None:
            return JSONResponse(
                content={"message": "No cover art found"}, status_code=404
            )

        result = {"release_id": release_id}

        for image in data.get("images", []):
            if image.get("front"):
                result.update(image)
                break

        return JSONResponse(content=result, status_code=200)
    except json.JSONDecodeError:
        return JSONResponse(
            content={"message": "Invalid JSON response"}, status_code=400
        )


async def get_current_playing(request: Request):
    query = """
    select title , artist , album , release_id , duration , playbackrate , bundle , elapsed , devicename , updated
    from events e
    where is_deleted = false
    and is_valid = true
    order by created desc
    limit 1;
    """
    data: List[Record] = None
    try:
        data = await request.app.db.fetch(query)
    except Exception as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}",
        )
    if not data:
        return JSONResponse(content={"message": "No current playing"}, status_code=404)
    response = jsonable_encoder(data[0])
    return JSONResponse(content=response, status_code=200)
