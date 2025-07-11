"""Song repository implementation using SQLAlchemy ORM"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ...domain.entities.song import Song
from ...domain.repositories.song_repository import ISongRepository
from ...domain.value_objects.entity_ids import SongId, UserId, OrderId
from ...domain.enums import MusicStyle, GenerationStatus, EmotionalTone
from ..orm.song_model import SongModel  # Fixed import for DDD architecture


class SongRepositoryImpl(ISongRepository):
    """Repository implementation for Song aggregate"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, song: Song) -> Song:
        """Save or update song"""
        existing = self.session.query(SongModel).filter(SongModel.id == song.id.value).first()
        
        if existing:
            # Update existing song
            self._update_model_from_entity(existing, song)
        else:
            # Create new song
            model = self._create_model_from_entity(song)
            self.session.add(model)
        
        self.session.flush()
        return song

    async def get_by_id(self, song_id: SongId) -> Optional[Song]:
        """Get song by ID"""
        model = self.session.query(SongModel).filter(SongModel.id == song_id.value).first()
        return self._map_to_entity(model) if model else None

    async def get_by_user_id(self, user_id: UserId) -> List[Song]:
        """Get songs by user ID"""
        models = self.session.query(SongModel).filter(SongModel.user_id == user_id.value).all()
        return [self._map_to_entity(model) for model in models]

    async def get_by_order_id(self, order_id: OrderId) -> Optional[Song]:
        """Get song by order ID"""
        model = self.session.query(SongModel).filter(SongModel.order_id == order_id.value).first()
        return self._map_to_entity(model) if model else None

    async def add(self, song: Song) -> Song:
        """Add a new song"""
        # Create model without ID for new songs
        model_data = {
            'user_id': song.user_id.value,
            'order_id': song.order_id.value,
            'title': song.title,
            'description': song.description,
            'music_style': song.music_style.value if song.music_style else None,
            'recipient_description': song.recipient_description,
            'occasion_description': song.occasion_description,
            'tone': song.tone.value if song.tone and hasattr(song.tone, 'value') else song.tone,
            'additional_details': song.additional_details,
            'lyrics': song.lyrics.content if song.lyrics else None,
            'audio_url': song.audio_url.url if song.audio_url else None,
            'video_url': song.video_url.url if song.video_url else None,
            'duration': song.duration.duration if song.duration else None,
            'lyrics_status': song.lyrics_status.value,
            'audio_status': song.audio_status.value,
            'video_status': song.video_status.value,
            'video_format': song.video_format,
            'image_count': song.image_count,
            'created_at': song.created_at,
            'updated_at': song.updated_at,
            'delivered_at': song.delivered_at
        }
        
        model = SongModel(**model_data)
        self.session.add(model)
        self.session.flush()
        
        # Return updated song with generated ID
        song.id = SongId(model.id)
        return song

    async def update(self, song: Song) -> Song:
        """Update an existing song"""
        existing = self.session.query(SongModel).filter(SongModel.id == song.id.value).first()
        if existing:
            self._update_model_from_entity(existing, song)
            self.session.flush()
        return song

    async def delete(self, song_id: SongId) -> None:
        """Delete song"""
        song = self.session.query(SongModel).filter(SongModel.id == song_id.value).first()
        if song:
            self.session.delete(song)

    async def count(self) -> int:
        """Count total songs"""
        return self.session.query(SongModel).count()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Song]:
        """Get all songs (legacy method)"""
        models = self.session.query(SongModel).offset(skip).limit(limit).all()
        return [self._map_to_entity(model) for model in models]

    def count_total_songs(self) -> int:
        """Count total songs (legacy method)"""
        return self.session.query(SongModel).count()

    def count_by_status(self, status: GenerationStatus) -> int:
        """Count songs by generation status (legacy method)"""
        return self.session.query(SongModel).filter(SongModel.generation_status == status.value).count()

    def delete_legacy(self, song_id: SongId) -> bool:
        """Delete song (legacy method)"""
        song = self.session.query(SongModel).filter(SongModel.id == song_id.value).first()
        if song:
            self.session.delete(song)
            return True
        return False

    def _create_model_from_entity(self, song: Song) -> SongModel:
        """Create ORM model from domain entity"""
        return SongModel(
            user_id=song.user_id.value,
            order_id=song.order_id.value,
            title=song.title,
            description=song.description,
            music_style=song.music_style.value if song.music_style else None,
            recipient_description=song.recipient_description,
            occasion_description=song.occasion_description,
            tone=song.tone.value if song.tone and hasattr(song.tone, 'value') else song.tone,
            additional_details=song.additional_details,
            lyrics=song.lyrics.content if song.lyrics else None,
            audio_url=song.audio_url.url if song.audio_url else None,
            video_url=song.video_url.url if song.video_url else None,
            duration=song.duration.duration if song.duration else None,
            lyrics_status=song.lyrics_status.value,
            audio_status=song.audio_status.value,
            video_status=song.video_status.value,
            video_format=song.video_format,
            image_count=song.image_count,
            created_at=song.created_at,
            updated_at=song.updated_at,
            delivered_at=song.delivered_at
        )

    def _update_model_from_entity(self, model: SongModel, song: Song) -> None:
        """Update ORM model from domain entity"""
        model.title = song.title
        model.description = song.description
        model.music_style = song.music_style.value if song.music_style else None
        model.recipient_description = song.recipient_description
        model.occasion_description = song.occasion_description
        model.tone = song.tone.value if song.tone and hasattr(song.tone, 'value') else song.tone
        model.additional_details = song.additional_details
        model.lyrics = song.lyrics.content if song.lyrics else None
        model.audio_url = song.audio_url.url if song.audio_url else None
        model.video_url = song.video_url.url if song.video_url else None
        model.duration = song.duration.duration if song.duration else None
        model.lyrics_status = song.lyrics_status.value
        model.audio_status = song.audio_status.value
        model.video_status = song.video_status.value
        model.video_format = song.video_format
        model.image_count = song.image_count
        model.updated_at = song.updated_at
        model.delivered_at = song.delivered_at

    def _map_to_entity(self, model: SongModel) -> Song:
        """Map ORM model to domain entity"""
        from ...domain.value_objects.song_content import Lyrics, AudioUrl, VideoUrl, Duration
        
        # Build value objects
        lyrics = Lyrics(model.lyrics) if model.lyrics else None
        audio_url = AudioUrl(model.audio_url) if model.audio_url else None
        video_url = VideoUrl(model.video_url) if model.video_url else None
        duration = Duration(model.duration) if model.duration else None
        
        return Song(
            id=SongId(model.id),
            user_id=UserId(model.user_id),
            order_id=OrderId(model.order_id),
            title=model.title,
            description=model.description or "",
            music_style=MusicStyle(model.music_style) if model.music_style else None,
            recipient_description=model.recipient_description,
            occasion_description=model.occasion_description,
            tone=EmotionalTone(model.tone) if model.tone else None,
            additional_details=model.additional_details,
            lyrics=lyrics,
            audio_url=audio_url,
            video_url=video_url,
            duration=duration,
            lyrics_status=GenerationStatus(model.lyrics_status),
            audio_status=GenerationStatus(model.audio_status),
            video_status=GenerationStatus(model.video_status),
            video_format=model.video_format,
            image_count=model.image_count or 0,
            created_at=model.created_at,
            updated_at=model.updated_at,
            delivered_at=model.delivered_at
        ) 