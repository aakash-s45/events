import base64
import json
import logging
import os
from typing import List, Optional, Tuple
import uuid
from asyncpg import Record
from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from requests import request

from cache import InMemoryCache
from constant import CURRENT_PLAYING_CACHE_KEY
from settings import (
    APP_URL,
    COVERT_ART_ARCHIVE_BASE_URL,
    LAST_FM_API_KEY,
    MUSICBRAINZ_BASE_URL,
    STATIC_DIR,
    THE_LAST_FM_BASE_URL,
)
from utils import guess_file_ext_from_base64, make_api_request
from validation import AddMusicModel

logger = logging.getLogger(__name__)

last_added: str = ""
cache_ttl = 3600


def save_cover_art(image_str: str):
    if not image_str:
        return None
    image_str = image_str.strip()

    file_ext = guess_file_ext_from_base64(image_str)
    filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(STATIC_DIR, filename)

    image_data = base64.b64decode(image_str)
    with open(file_path, "wb") as f:
        f.write(image_data)

    return {"filename": filename, "file_path": file_path}


async def add_music(request: Request, data: AddMusicModel):
    global last_added
    key = f"{data.title}-{data.artist}-{data.album}-{data.playbackRate}"
    if not data.duration:
        return JSONResponse(content={"message": "Missing duration"}, status_code=400)
    if key == last_added:
        logger.info(f"Duplicate request for {key}, skipping")
        return JSONResponse(content={"message": "Duplicate request"}, status_code=200)
    
    last_added = key
    status, msg, validated_data = validate_music(data)
    if not status:
        logger.error(f"Validation error: {msg}")

    if not validated_data.get("images") and data.artworkUrl:
        validated_data["images"] = [
            {
                "size": "normal",
                "#text": data.artworkUrl,
            },
        ]


    if not validated_data.get("images") and data.image:
        response = save_cover_art(data.image)
        if response:
            validated_data["images"] = [
                {
                    "size": "normal",
                    "#text": f"{APP_URL}/static/{response.get('filename')}",
                },
            ]

    query = """
        INSERT INTO events
        (title, recording_id, artist, artist_id, album, release_id, duration, playbackRate, bundle, elapsed, deviceName, images, is_valid, playcount) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 1)
        ON CONFLICT (title, artist, album)
        DO UPDATE SET 
        playbackRate = $8, bundle = $9, elapsed = $10, deviceName = $11, images = $12,
        playcount = events.playcount + 1, updated = now();
    """
    db_data = {
        "title": data.title or validated_data["title"],
        "recording_id": validated_data.get("recording_id"),
        "artist": data.artist or validated_data.get("artist"),
        "artist_id": validated_data.get("artist_id"),
        "album": data.album or validated_data.get("album"),
        "release_id": validated_data.get("release_id"),
        "duration": data.duration or validated_data.get("duration"),
        "playbackRate": validated_data.get("playbackRate"),
        "bundle": validated_data.get("bundle"),
        "elapsed": data.elapsed or validated_data.get("elapsed"),
        "deviceName": validated_data.get("deviceName"),
        "images": (
            json.dumps(validated_data.get("images"))
            if validated_data.get("images")
            else None
        ),
        "is_valid": status,
    }

    try:
        async with request.app.db.acquire() as con:
            await con.execute(query, *db_data.values())
    except Exception as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}",
        )
    
    request.app.cache.delete(CURRENT_PLAYING_CACHE_KEY)
    return JSONResponse(content={"message": "Data saved successfully"}, status_code=200)


def validate_music(data: AddMusicModel):
    # status, msg, resp = lookup_track_mb(data.title, data.artist, data.album or "")
    status, msg, resp = lookup_track_lastfm(data.title, data.artist)
    if not status:
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
        if retry > 0:
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
                return True, "success", result
        return False, "No results found", {}
    except json.JSONDecodeError:
        return False, "Invalid JSON response", {}
    return False, "No results found", {}


# Lookup Track from last.fm
def lookup_track_lastfm(title: str, artist: str, retry: int = 5) -> Tuple[str, dict]:
    if retry < 0:
        return False, "No results found after multiple attempts", {}
    base_url = f"{THE_LAST_FM_BASE_URL}/2.0"

    params = {
        "format": "json",
        "method": "track.getInfo",
        "api_key": LAST_FM_API_KEY,
        "artist": artist,
        "track": title,
    }

    status, reason, response = make_api_request(base_url, "GET", params=params)
    if not status:
        if retry:
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
        result["duration"] = float(data.get("duration", 0)) / 1000
        result["images"] = data.get("album", {}).get("image", [])
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
    select title , artist , album , release_id , duration , playbackrate , elapsed , devicename , updated, images
    from events e
    where is_deleted = false
    and is_valid = true
    order by updated desc
    limit 1;
    """
    cache: InMemoryCache = request.app.cache
    cached = cache.get(CURRENT_PLAYING_CACHE_KEY)
    if cached:
        return JSONResponse(content=cached, status_code=200)
    
    data: List[Record] = None
    try:
        async with request.app.db.acquire() as con:
            data = await con.fetch(query)
    except Exception as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}",
        )
    if not data:
        return JSONResponse(content={"message": "No current playing"}, status_code=404)
    response = jsonable_encoder(data[0])
    response["images"] = (
        json.loads(response.get("images")) if response.get("images") else None
    )
    image_url = response.get("images")[-1].get("#text") if response.get("images") else None
    static_image_url = download_and_save_image(image_url)    # if image is present, download the image and store it locally, and serve the static local url
    if static_image_url:
        response.pop("images", None)
        host = request.headers.get("host")
        if not host:
            response['artwork'] = static_image_url
        if "local" in host:
            response['artwork'] = "http://" + host + static_image_url
        else:
            response['artwork'] = "https://" + host + static_image_url

    cache.set(CURRENT_PLAYING_CACHE_KEY, response, ttl=cache_ttl)

    return JSONResponse(content=response, status_code=200)


def download_and_save_image(image_url: str, image_filename: str = 'current_playing.png'):
    """
    - delete the image at static path if present with the same filename
    - Download the image from the given URL
    - Save the image to the specified filename
    - Return the local static link
    """
    
    if not image_url:
        return None
    
    response = request('GET', image_url)
    if response.status_code != 200:
        return None
    
    static_path = os.path.join(STATIC_DIR, image_filename)
    with open(static_path, 'wb') as f:
        f.write(response.content)
    
    return f"/static/{image_filename}"
    