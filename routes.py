from fastapi import APIRouter, Request

from service import add_music, get_cover_art, get_current_playing
from validation import AddMusicModel


api_v1 = APIRouter()


@api_v1.get("/health")
async def health():
    return {"status": "ok"}


@api_v1.get("/version")
async def version():
    return {"version": "1.0.0"}


@api_v1.post("/add-music")
async def _add_music(request: Request, data: AddMusicModel):
    return await add_music(request, data)


@api_v1.get("/cover-art/{release_id}")
async def _get_cover_art(request: Request, release_id: str):
    return await get_cover_art(request, release_id)


@api_v1.get("/current-playing")
async def _get_current_playing(request: Request):
    return await get_current_playing(request) 