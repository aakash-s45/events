from typing import Optional
from pydantic import BaseModel


class AddMusicModel(BaseModel):
    title: str
    artist: str
    album: Optional[str] = ""
    duration: Optional[float] = 0.0
    playbackRate: Optional[bool] = False
    bundle: Optional[str] = ""
    elapsed: Optional[float] = 0.0
    deviceName: Optional[str] = ""
    artworkUrl: Optional[str] = ""
    pageTitle: Optional[str] = ""
    image: Optional[str] = ""


class GetCoverArtModel(BaseModel):
    # mbid of album
    release_id: Optional[str] = ""


class EmailRequest(BaseModel):
    email: str
    subject: str
    body: str