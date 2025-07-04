"""Song entity with generation business logic"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from ..value_objects.entity_ids import SongId, UserId, OrderId
from ..value_objects.song_content import Lyrics, AudioUrl, VideoUrl, Duration
from ..enums import MusicStyle, GenerationStatus, EmotionalTone
from ..events.song_events import (
    LyricsGenerationStarted, LyricsGenerationCompleted,
    AudioGenerationStarted, AudioGenerationCompleted,
    VideoGenerationStarted, VideoGenerationCompleted,
    SongDelivered
)


@dataclass
class Song:
    id: SongId
    user_id: UserId
    order_id: OrderId
    
    # Basic song info
    title: Optional[str] = None
    description: str = ""
    music_style: Optional[MusicStyle] = None
    
    # Song creation form data (Step 1 from your spec)
    recipient_description: Optional[str] = None
    occasion_description: Optional[str] = None
    tone: Optional[EmotionalTone] = None
    additional_details: Optional[str] = None
    
    # Generated content
    lyrics: Optional[Lyrics] = None
    audio_url: Optional[AudioUrl] = None
    video_url: Optional[VideoUrl] = None
    duration: Optional[Duration] = None
    
    # Generation status tracking (separate for each phase)
    lyrics_status: GenerationStatus = GenerationStatus.NOT_STARTED
    audio_status: GenerationStatus = GenerationStatus.NOT_STARTED
    video_status: GenerationStatus = GenerationStatus.NOT_STARTED
    
    # Video generation metadata
    video_format: Optional[str] = None  # '16:9' or '9:16'
    image_count: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None
    
    # Domain events
    _events: List = field(default_factory=list, init=False)
    
    # Computed property for backward compatibility
    @property
    def generation_status(self) -> GenerationStatus:
        """Overall generation status based on individual statuses"""
        if self.lyrics_status == GenerationStatus.FAILED or \
           self.audio_status == GenerationStatus.FAILED or \
           self.video_status == GenerationStatus.FAILED:
            return GenerationStatus.FAILED
        
        if self.lyrics_status == GenerationStatus.COMPLETED and \
           self.audio_status == GenerationStatus.COMPLETED and \
           (self.video_status == GenerationStatus.COMPLETED or self.video_status == GenerationStatus.NOT_STARTED):
            return GenerationStatus.COMPLETED
        
        if self.lyrics_status != GenerationStatus.NOT_STARTED or \
           self.audio_status != GenerationStatus.NOT_STARTED or \
           self.video_status != GenerationStatus.NOT_STARTED:
            return GenerationStatus.IN_PROGRESS
        
        return GenerationStatus.NOT_STARTED
    
    def start_lyrics_generation(self) -> None:
        """Business logic: start lyrics generation"""
        if self.lyrics_status != GenerationStatus.NOT_STARTED:
            raise ValueError("Lyrics generation already started")
        
        self.lyrics_status = GenerationStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()
        
        self._events.append(LyricsGenerationStarted(
            song_id=self.id,
            user_id=self.user_id,
            music_style=self.music_style
        ))
    
    def complete_lyrics_generation(self, lyrics: Lyrics) -> None:
        """Business logic: complete lyrics generation"""
        if self.lyrics_status != GenerationStatus.IN_PROGRESS:
            raise ValueError("Lyrics generation not in progress")
        
        self.lyrics = lyrics
        self.lyrics_status = GenerationStatus.COMPLETED
        self.updated_at = datetime.utcnow()
        
        self._events.append(LyricsGenerationCompleted(
            song_id=self.id,
            user_id=self.user_id,
            lyrics=lyrics
        ))
    
    def start_audio_generation(self) -> None:
        """Business logic: start audio generation"""
        if self.lyrics_status != GenerationStatus.COMPLETED:
            raise ValueError("Need completed lyrics before audio")
        
        if self.audio_status != GenerationStatus.NOT_STARTED:
            raise ValueError("Audio generation already started")
        
        self.audio_status = GenerationStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()
        
        self._events.append(AudioGenerationStarted(
            song_id=self.id,
            user_id=self.user_id,
            lyrics=self.lyrics,
            music_style=self.music_style
        ))
    
    def complete_audio_generation(self, audio_url: AudioUrl, duration: Duration) -> None:
        """Business logic: complete audio generation"""
        if self.audio_status != GenerationStatus.IN_PROGRESS:
            raise ValueError("Audio generation not in progress")
        
        self.audio_url = audio_url
        self.duration = duration
        self.audio_status = GenerationStatus.COMPLETED
        self.updated_at = datetime.utcnow()
        
        self._events.append(AudioGenerationCompleted(
            song_id=self.id,
            user_id=self.user_id,
            audio_url=audio_url,
            duration=duration
        ))
    
    def start_video_generation(self, video_format: str = "16:9") -> None:
        """Business logic: start video generation"""
        if self.audio_status != GenerationStatus.COMPLETED:
            raise ValueError("Need completed audio before video")
        
        if self.video_status != GenerationStatus.NOT_STARTED:
            raise ValueError("Video generation already started")
        
        self.video_status = GenerationStatus.IN_PROGRESS
        self.video_format = video_format
        self.updated_at = datetime.utcnow()
        
        self._events.append(VideoGenerationStarted(
            song_id=self.id,
            user_id=self.user_id,
            audio_url=self.audio_url,
            image_count=self.image_count,
            video_format=video_format
        ))
    
    def complete_video_generation(self, video_url: VideoUrl) -> None:
        """Business logic: complete video generation"""
        if self.video_status != GenerationStatus.IN_PROGRESS:
            raise ValueError("Video generation not in progress")
        
        self.video_url = video_url
        self.video_status = GenerationStatus.COMPLETED
        self.updated_at = datetime.utcnow()
        
        self._events.append(VideoGenerationCompleted(
            song_id=self.id,
            user_id=self.user_id,
            video_url=video_url
        ))
    
    def mark_as_delivered(self) -> None:
        """Business logic: mark song as delivered"""
        if not self.is_ready_for_delivery:
            raise ValueError("Song not ready for delivery")
        
        self.delivered_at = datetime.utcnow()
        
        self._events.append(SongDelivered(
            song_id=self.id,
            user_id=self.user_id,
            delivered_at=self.delivered_at
        ))
    
    def set_image_count(self, count: int) -> None:
        """Set the number of uploaded images"""
        self.image_count = count
        self.updated_at = datetime.utcnow()
    
    @property
    def is_ready_for_delivery(self) -> bool:
        """Check if song is ready for delivery"""
        # For audio-only, just need lyrics and audio completed
        # For video, need all three completed
        audio_ready = (self.lyrics_status == GenerationStatus.COMPLETED and 
                      self.audio_status == GenerationStatus.COMPLETED)
        
        if self.image_count > 0:  # Video requested
            return audio_ready and self.video_status == GenerationStatus.COMPLETED
        else:  # Audio only
            return audio_ready
    
    @property
    def requires_video(self) -> bool:
        """Check if video generation is required"""
        return self.image_count > 0
    
    def get_events(self) -> List:
        """Get and clear domain events"""
        events = self._events.copy()
        self._events.clear()
        return events 