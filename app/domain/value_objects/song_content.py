"""Song content value objects"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..enums import MusicStyle


@dataclass(frozen=True)
class Lyrics:
    content: str
    
    def __post_init__(self):
        if len(self.content.strip()) < 10:
            raise ValueError("Lyrics must be at least 10 characters")
        if len(self.content) > 5000:
            raise ValueError("Lyrics too long")
    
    @property
    def word_count(self) -> int:
        return len(self.content.split())


@dataclass(frozen=True)
class AudioUrl:
    url: str
    
    def __post_init__(self):
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format")


@dataclass(frozen=True)
class VideoUrl:
    url: str
    
    def __post_init__(self):
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format")


@dataclass(frozen=True)
class Duration:
    duration: float
    
    def __post_init__(self):
        if self.duration < 0:
            raise ValueError("Duration cannot be negative")
    
    @property
    def minutes(self) -> float:
        return self.duration / 60


@dataclass(frozen=True)
class SongContent:
    """Composite value object for song content"""
    description: str
    music_style: MusicStyle
    lyrics: Optional[Lyrics] = None
    audio_url: Optional[AudioUrl] = None
    video_url: Optional[VideoUrl] = None
    duration: Optional[Duration] = None
    
    def __post_init__(self):
        if not self.description or len(self.description.strip()) < 10:
            raise ValueError("Description must be at least 10 characters")
        if len(self.description) > 2000:
            raise ValueError("Description too long") 