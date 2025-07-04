"""Create all tables - simple schema

Revision ID: 281f8184f079
Revises: 
Create Date: 2025-07-03 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '281f8184f079'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create comprehensive database schema with string columns"""
    
    # Create users table with password reset functionality
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='pending_verification', nullable=False),
        sa.Column('role', sa.String(), server_default='user', nullable=False),
        sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('email_verification_token', sa.String(), nullable=True),
        
        # Password reset fields for production use
        sa.Column('password_reset_token', sa.String(), nullable=True),
        sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_reset_used', sa.Boolean(), server_default='false', nullable=False),
        
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create orders table
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_type', sa.String(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('lemon_squeezy_order_id', sa.String(), nullable=True),
        sa.Column('lemon_squeezy_payment_id', sa.String(), nullable=True),
        sa.Column('payment_provider_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lemon_squeezy_order_id'),
        sa.UniqueConstraint('lemon_squeezy_payment_id')
    )
    
    # Create songs table
    op.create_table('songs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('music_style', sa.String(), nullable=False),
        sa.Column('lyrics', sa.Text(), nullable=True),
        sa.Column('audio_url', sa.String(), nullable=True),
        sa.Column('video_url', sa.String(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        
        # Song creation form fields
        sa.Column('recipient_description', sa.Text(), nullable=True),
        sa.Column('occasion_description', sa.Text(), nullable=True),
        sa.Column('tone', sa.String(), nullable=True),
        sa.Column('additional_details', sa.Text(), nullable=True),
        
        # Generation status tracking
        sa.Column('generation_status', sa.String(), nullable=True),
        sa.Column('lyrics_status', sa.String(), server_default='not_started', nullable=False),
        sa.Column('audio_status', sa.String(), server_default='not_started', nullable=False),
        sa.Column('video_status', sa.String(), server_default='not_started', nullable=False),
        
        # Video generation metadata
        sa.Column('video_format', sa.String(), nullable=True),
        sa.Column('image_count', sa.Integer(), server_default='0', nullable=True),
        
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create song_images table
    op.create_table('song_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('song_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_url', sa.String(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('details', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create email_verifications table
    op.create_table('email_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    
    # Create task_results table
    op.create_table('task_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('task_name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('result', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    
    # Create indexes for optimal performance
    
    # Users indexes
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_email_verified', 'users', ['email_verified'])
    op.create_index('idx_users_password_reset_token', 'users', ['password_reset_token'])
    
    # Orders indexes
    op.create_index('ix_orders_id', 'orders', ['id'])
    op.create_index('idx_orders_user_id_created_at', 'orders', ['user_id', 'created_at'])
    op.create_index('idx_orders_status_created_at', 'orders', ['status', 'created_at'])
    op.create_index('idx_orders_payment_provider_id', 'orders', ['payment_provider_id'])
    
    # Songs indexes
    op.create_index('ix_songs_id', 'songs', ['id'])
    op.create_index('idx_songs_user_id_created_at', 'songs', ['user_id', 'created_at'])
    op.create_index('idx_songs_generation_status_created_at', 'songs', ['generation_status', 'created_at'])
    op.create_index('idx_songs_lyrics_status', 'songs', ['lyrics_status'])
    op.create_index('idx_songs_audio_status', 'songs', ['audio_status'])
    op.create_index('idx_songs_video_status', 'songs', ['video_status'])
    
    # Song Images indexes
    op.create_index('ix_song_images_id', 'song_images', ['id'])
    op.create_index('idx_song_images_song_id_order', 'song_images', ['song_id', 'order_index'])
    
    # Other indexes
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_email_verifications_id', 'email_verifications', ['id'])
    op.create_index('ix_task_results_id', 'task_results', ['id'])


def downgrade() -> None:
    """Drop all tables"""
    
    # Drop indexes first
    op.drop_index('ix_task_results_id', table_name='task_results')
    op.drop_index('ix_email_verifications_id', table_name='email_verifications')
    op.drop_index('ix_audit_logs_id', table_name='audit_logs')
    op.drop_index('idx_song_images_song_id_order', table_name='song_images')
    op.drop_index('ix_song_images_id', table_name='song_images')
    op.drop_index('idx_songs_video_status', table_name='songs')
    op.drop_index('idx_songs_audio_status', table_name='songs')
    op.drop_index('idx_songs_lyrics_status', table_name='songs')
    op.drop_index('idx_songs_generation_status_created_at', table_name='songs')
    op.drop_index('idx_songs_user_id_created_at', table_name='songs')
    op.drop_index('ix_songs_id', table_name='songs')
    op.drop_index('idx_orders_payment_provider_id', table_name='orders')
    op.drop_index('idx_orders_status_created_at', table_name='orders')
    op.drop_index('idx_orders_user_id_created_at', table_name='orders')
    op.drop_index('ix_orders_id', table_name='orders')
    op.drop_index('idx_users_password_reset_token', table_name='users')
    op.drop_index('idx_users_email_verified', table_name='users')
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index('idx_users_status', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    
    # Drop tables
    op.drop_table('task_results')
    op.drop_table('email_verifications')
    op.drop_table('audit_logs')
    op.drop_table('song_images')
    op.drop_table('songs')
    op.drop_table('orders')
    op.drop_table('users')
