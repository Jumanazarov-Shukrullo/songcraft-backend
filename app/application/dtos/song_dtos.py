"""Song DTOs for API requests and responses"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from ...domain.enums import MusicStyle, GenerationStatus, EmotionalTone


class CreateSongRequest(BaseModel):
    """Request DTO for creating a song from client"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=2000, alias='story')
    music_style: MusicStyle = Field(..., alias='style')
    lyrics: Optional[str] = None  # when client supplies their own lyrics
    
    # Song creation form fields (Step 1)
    recipient_description: Optional[str] = Field(None, max_length=1000)
    occasion_description: Optional[str] = Field(None, max_length=1000) 
    additional_details: Optional[str] = Field(None, max_length=500)
    
    # Emotional tone (Step 3)
    tone: Optional[EmotionalTone] = None

    class Config:
        use_enum_values = True
        populate_by_name = True


class SongResponse(BaseModel):
    """Response DTO for song data"""
    id: UUID
    user_id: UUID
    order_id: UUID
    title: Optional[str] = None
    description: str
    music_style: str
    status: str
    lyrics_status: Optional[str] = None
    audio_status: Optional[str] = None
    video_status: Optional[str] = None
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
    order_id: UUID

    class Config:
        use_enum_values = True


class SongResponseDTO(BaseModel):
    """Alternative naming for backward compatibility"""
    id: UUID
    user_id: UUID
    order_id: UUID
    title: Optional[str] = None
    description: str
    music_style: str
    status: str
    lyrics_status: Optional[str] = None
    audio_status: Optional[str] = None
    video_status: Optional[str] = None
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