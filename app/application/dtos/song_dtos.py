"""Song DTOs for API requests and responses"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from ...domain.enums import MusicStyle, GenerationStatus


class CreateSongRequest(BaseModel):
    """Request DTO for creating a song"""
    description: str = Field(..., min_length=1, max_length=2000)
    music_style: MusicStyle
    order_id: int

    class Config:
        use_enum_values = True


class SongResponse(BaseModel):
    """Response DTO for song data"""
    id: int
    user_id: int
    order_id: int
    description: str
    music_style: str
    status: str
    lyrics: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SongUpdateRequest(BaseModel):
    """Request DTO for updating a song"""
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    music_style: Optional[MusicStyle] = None
    lyrics: Optional[str] = None

    class Config:
        use_enum_values = True


class SongCreateDTO(BaseModel):
    """Alternative naming for backward compatibility"""
    description: str = Field(..., min_length=1, max_length=2000)
    music_style: MusicStyle
    order_id: int

    class Config:
        use_enum_values = True


class SongResponseDTO(BaseModel):
    """Alternative naming for backward compatibility"""
    id: int
    user_id: int
    order_id: int
    description: str
    music_style: str
    status: str
    lyrics: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerateLyricsRequest(BaseModel):
    """DTO for generating lyrics"""
    description: str
    music_style: str 