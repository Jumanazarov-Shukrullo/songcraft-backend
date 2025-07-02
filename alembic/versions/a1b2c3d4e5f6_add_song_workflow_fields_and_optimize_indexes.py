"""add song workflow fields and optimize indexes

Revision ID: a1b2c3d4e5f6
Revises: 9d17c043476a
Create Date: 2025-01-21 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9d17c043476a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Create new enum type ###
    
    # Create EmotionalTone enum
    emotional_tone_enum = sa.Enum('emotional', 'romantic', 'playful', 'ironic', name='emotionaltone')
    emotional_tone_enum.create(op.get_bind())
    
    # ### Add new columns to Songs table ###
    
    # Basic song info
    op.add_column('songs', sa.Column('title', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))
    
    # Song creation form fields
    op.add_column('songs', sa.Column('recipient_description', sa.Text(), nullable=True))
    op.add_column('songs', sa.Column('occasion_description', sa.Text(), nullable=True))
    op.add_column('songs', sa.Column('tone', sa.Enum('emotional', 'romantic', 'playful', 'ironic', name='emotionaltone'), nullable=True))
    op.add_column('songs', sa.Column('additional_details', sa.Text(), nullable=True))
    
    # Detailed generation status fields (reusing existing GenerationStatus enum)
    op.add_column('songs', sa.Column('lyrics_status', sa.Enum('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='generationstatus'), 
                                     server_default='NOT_STARTED', nullable=False))
    op.add_column('songs', sa.Column('audio_status', sa.Enum('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='generationstatus'), 
                                     server_default='NOT_STARTED', nullable=False))
    op.add_column('songs', sa.Column('video_status', sa.Enum('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='generationstatus'), 
                                     server_default='NOT_STARTED', nullable=False))
    
    # Video generation metadata
    op.add_column('songs', sa.Column('video_format', sa.String(), nullable=True))
    op.add_column('songs', sa.Column('image_count', sa.Integer(), server_default='0', nullable=True))
    
    # ### Add new column to Orders table ###
    
    # Add payment_provider_id for domain compatibility
    op.add_column('orders', sa.Column('payment_provider_id', sa.String(), nullable=True))
    
    # ### Add Performance Indexes ###
    
    # Songs indexes
    op.create_index('idx_songs_user_id_created_at', 'songs', ['user_id', 'created_at'])
    op.create_index('idx_songs_generation_status_created_at', 'songs', ['generation_status', 'created_at'])
    op.create_index('idx_songs_lyrics_status', 'songs', ['lyrics_status'])
    op.create_index('idx_songs_audio_status', 'songs', ['audio_status'])
    op.create_index('idx_songs_video_status', 'songs', ['video_status'])
    
    # Orders indexes
    op.create_index('idx_orders_user_id_created_at', 'orders', ['user_id', 'created_at'])
    op.create_index('idx_orders_status_created_at', 'orders', ['status', 'created_at'])
    op.create_index('idx_orders_payment_provider_id', 'orders', ['payment_provider_id'])
    
    # Users indexes
    op.create_index('idx_users_email_verified', 'users', ['email_verified'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_role', 'users', ['role'])
    
    # Song Images indexes
    op.create_index('idx_song_images_song_id_order', 'song_images', ['song_id', 'order_index'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_song_images_song_id_order', table_name='song_images')
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index('idx_users_status', table_name='users')
    op.drop_index('idx_users_email_verified', table_name='users')
    op.drop_index('idx_orders_payment_provider_id', table_name='orders')
    op.drop_index('idx_orders_status_created_at', table_name='orders')
    op.drop_index('idx_orders_user_id_created_at', table_name='orders')
    op.drop_index('idx_songs_video_status', table_name='songs')
    op.drop_index('idx_songs_audio_status', table_name='songs')
    op.drop_index('idx_songs_lyrics_status', table_name='songs')
    op.drop_index('idx_songs_generation_status_created_at', table_name='songs')
    op.drop_index('idx_songs_user_id_created_at', table_name='songs')
    
    # Drop new columns
    op.drop_column('orders', 'payment_provider_id')
    op.drop_column('songs', 'image_count')
    op.drop_column('songs', 'video_format')
    op.drop_column('songs', 'additional_details')
    op.drop_column('songs', 'tone')
    op.drop_column('songs', 'occasion_description')
    op.drop_column('songs', 'recipient_description')
    op.drop_column('songs', 'video_status')
    op.drop_column('songs', 'audio_status')
    op.drop_column('songs', 'lyrics_status')
    op.drop_column('songs', 'updated_at')
    op.drop_column('songs', 'title')
    
    # Drop enum
    sa.Enum(name='emotionaltone').drop(op.get_bind(), checkfirst=True) 