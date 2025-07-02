"""Song domain events"""

from dataclasses import dataclass
from datetime import datetime

from ..value_objects.entity_ids import SongId, UserId
from ..value_objects.song_content import Lyrics, AudioUrl, VideoUrl
from ..enums import MusicStyle


@dataclass(frozen=True)
class LyricsGenerationStarted:
    song_id: SongId
    user_id: UserId
    music_style: MusicStyle


@dataclass(frozen=True)
class LyricsGenerationCompleted:
    song_id: SongId
    user_id: UserId
    lyrics: Lyrics


@dataclass(frozen=True)
class AudioGenerationStarted:
    song_id: SongId
    user_id: UserId
    lyrics: Lyrics
    music_style: MusicStyle


@dataclass(frozen=True)
class AudioGenerationCompleted:
    song_id: SongId
    user_id: UserId
    audio_url: AudioUrl
    duration: float


@dataclass(frozen=True)
class VideoGenerationStarted:
    song_id: SongId
    user_id: UserId
    audio_url: AudioUrl
    image_count: int
    video_format: str


@dataclass(frozen=True)
class VideoGenerationCompleted:
    song_id: SongId
    user_id: UserId
    video_url: VideoUrl


@dataclass(frozen=True)
class SongDelivered:
    song_id: SongId
    user_id: UserId
    delivered_at: datetime 