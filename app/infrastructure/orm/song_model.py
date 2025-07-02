"""Song ORM Model"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...db.models import Base
from ...domain.enums import MusicStyle, GenerationStatus, EmotionalTone


class SongModel(Base):
    __tablename__ = 'songs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    
    # Basic song info
    title = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    music_style = Column(SQLEnum(MusicStyle), nullable=False)
    
    # Song creation form data (Step 1)
    recipient_description = Column(Text, nullable=True)
    occasion_description = Column(Text, nullable=True) 
    tone = Column(SQLEnum(EmotionalTone), nullable=True)
    additional_details = Column(Text, nullable=True)
    
    # Generated content
    lyrics = Column(Text, nullable=True)
    audio_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    
    # Generation status tracking
    generation_status = Column(SQLEnum(GenerationStatus), default=GenerationStatus.NOT_STARTED, index=True)
    lyrics_status = Column(SQLEnum(GenerationStatus), default=GenerationStatus.NOT_STARTED, nullable=False, index=True)
    audio_status = Column(SQLEnum(GenerationStatus), default=GenerationStatus.NOT_STARTED, nullable=False, index=True)
    video_status = Column(SQLEnum(GenerationStatus), default=GenerationStatus.NOT_STARTED, nullable=False, index=True)
    
    # Video generation metadata
    video_format = Column(String, nullable=True)  # '16:9' or '9:16'
    image_count = Column(Integer, default=0, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    delivered_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship('UserModel', back_populates='songs')
    order = relationship('OrderModel', back_populates='song')
    images = relationship('SongImageModel', back_populates='song', cascade='all, delete-orphan')


class SongImageModel(Base):
    __tablename__ = 'song_images'
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey('songs.id'), nullable=False)
    file_url = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    song = relationship('SongModel', back_populates='images')
