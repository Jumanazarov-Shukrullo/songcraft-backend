"""Convert all integer IDs to UUID

Revision ID: convert_ids_to_uuid
Revises: e386d9925d7f
Create Date: 2025-01-07 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision ='convert_ids_to_uuid'
down_revision = 'e386d9925d7f'
branch_labels = None
depends_on = None


def upgrade():
    """Convert integer IDs to UUIDs"""
    
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Step 1: Add temporary UUID columns
    op.add_column('users', sa.Column('id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('orders', sa.Column('id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('orders', sa.Column('user_id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('songs', sa.Column('id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('songs', sa.Column('user_id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('songs', sa.Column('order_id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('song_images', sa.Column('id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('song_images', sa.Column('song_id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('feedback', sa.Column('id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('feedback', sa.Column('user_id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('audit_logs', sa.Column('id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('audit_logs', sa.Column('user_id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('user_id_temp', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Step 2: Generate UUIDs for all existing records
    op.execute('UPDATE users SET id_temp = uuid_generate_v4()')
    op.execute('UPDATE orders SET id_temp = uuid_generate_v4()')
    op.execute('UPDATE songs SET id_temp = uuid_generate_v4()')
    op.execute('UPDATE song_images SET id_temp = uuid_generate_v4()')
    op.execute('UPDATE feedback SET id_temp = uuid_generate_v4()')
    op.execute('UPDATE audit_logs SET id_temp = uuid_generate_v4()')
    op.execute('UPDATE password_reset_tokens SET id_temp = uuid_generate_v4()')
    
    # Step 3: Update foreign key references
    # Map integer user IDs to UUID user IDs
    op.execute('''
        UPDATE orders 
        SET user_id_temp = users.id_temp 
        FROM users 
        WHERE orders.user_id = users.id
    ''')
    
    op.execute('''
        UPDATE songs 
        SET user_id_temp = users.id_temp 
        FROM users 
        WHERE songs.user_id = users.id
    ''')
    
    op.execute('''
        UPDATE songs 
        SET order_id_temp = orders.id_temp 
        FROM orders 
        WHERE songs.order_id = orders.id
    ''')
    
    op.execute('''
        UPDATE song_images 
        SET song_id_temp = songs.id_temp 
        FROM songs 
        WHERE song_images.song_id = songs.id
    ''')
    
    op.execute('''
        UPDATE feedback 
        SET user_id_temp = users.id_temp 
        FROM users 
        WHERE feedback.user_id = users.id
    ''')
    
    op.execute('''
        UPDATE audit_logs 
        SET user_id_temp = users.id_temp 
        FROM users 
        WHERE audit_logs.user_id = users.id
    ''')
    
    op.execute('''
        UPDATE password_reset_tokens 
        SET user_id_temp = users.id_temp 
        FROM users 
        WHERE password_reset_tokens.user_id = users.id
    ''')
    
    # Step 4: Drop foreign key constraints
    op.drop_constraint('orders_user_id_fkey', 'orders', type_='foreignkey')
    op.drop_constraint('songs_user_id_fkey', 'songs', type_='foreignkey')
    op.drop_constraint('songs_order_id_fkey', 'songs', type_='foreignkey')
    op.drop_constraint('song_images_song_id_fkey', 'song_images', type_='foreignkey')
    op.drop_constraint('feedback_user_id_fkey', 'feedback', type_='foreignkey')
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')
    op.drop_constraint('password_reset_tokens_user_id_fkey', 'password_reset_tokens', type_='foreignkey')
    
    # Step 5: Drop existing indexes that we need to recreate
    # Users table indexes
    op.drop_index('ix_users_id', table_name='users')
    
    # Orders table indexes
    op.drop_index('ix_orders_id', table_name='orders')
    op.drop_index('idx_orders_user_id_created_at', table_name='orders')
    op.drop_index('idx_orders_status_created_at', table_name='orders')
    op.drop_index('idx_orders_payment_provider_id', table_name='orders')
    
    # Songs table indexes
    op.drop_index('ix_songs_id', table_name='songs')
    op.drop_index('idx_songs_user_id_created_at', table_name='songs')
    op.drop_index('idx_songs_generation_status_created_at', table_name='songs')
    op.drop_index('idx_songs_audio_status', table_name='songs')
    op.drop_index('idx_songs_lyrics_status', table_name='songs')
    op.drop_index('idx_songs_video_status', table_name='songs')
    
    # Song images table indexes
    op.drop_index('idx_song_images_song_id_order', table_name='song_images')
    
    # Feedback table indexes
    op.drop_index('ix_feedback_id', table_name='feedback')
    op.drop_index('idx_feedback_user_id', table_name='feedback')
    op.drop_index('idx_feedback_status_created_at', table_name='feedback')
    
    # Audit logs table indexes
    op.drop_index('ix_audit_logs_id', table_name='audit_logs')
    
    # Password reset tokens table indexes
    op.drop_index('ix_password_reset_tokens_id', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_index('idx_password_reset_tokens_expires_at', table_name='password_reset_tokens')
    op.drop_index('idx_password_reset_tokens_user_used', table_name='password_reset_tokens')
    
    # Drop primary key constraints
    op.drop_constraint('users_pkey', 'users', type_='primary')
    op.drop_constraint('orders_pkey', 'orders', type_='primary')
    op.drop_constraint('songs_pkey', 'songs', type_='primary')
    op.drop_constraint('song_images_pkey', 'song_images', type_='primary')
    op.drop_constraint('feedback_pkey', 'feedback', type_='primary')
    op.drop_constraint('audit_logs_pkey', 'audit_logs', type_='primary')
    op.drop_constraint('password_reset_tokens_pkey', 'password_reset_tokens', type_='primary')
    
    # Drop old columns
    op.drop_column('users', 'id')
    op.drop_column('orders', 'id')
    op.drop_column('orders', 'user_id')
    op.drop_column('songs', 'id')
    op.drop_column('songs', 'user_id')
    op.drop_column('songs', 'order_id')
    op.drop_column('song_images', 'id')
    op.drop_column('song_images', 'song_id')
    op.drop_column('feedback', 'id')
    op.drop_column('feedback', 'user_id')
    op.drop_column('audit_logs', 'id')
    op.drop_column('audit_logs', 'user_id')
    op.drop_column('password_reset_tokens', 'id')
    op.drop_column('password_reset_tokens', 'user_id')
    
    # Step 6: Rename temp columns to final names
    op.alter_column('users', 'id_temp', new_column_name='id')
    op.alter_column('orders', 'id_temp', new_column_name='id')
    op.alter_column('orders', 'user_id_temp', new_column_name='user_id')
    op.alter_column('songs', 'id_temp', new_column_name='id')
    op.alter_column('songs', 'user_id_temp', new_column_name='user_id')
    op.alter_column('songs', 'order_id_temp', new_column_name='order_id')
    op.alter_column('song_images', 'id_temp', new_column_name='id')
    op.alter_column('song_images', 'song_id_temp', new_column_name='song_id')
    op.alter_column('feedback', 'id_temp', new_column_name='id')
    op.alter_column('feedback', 'user_id_temp', new_column_name='user_id')
    op.alter_column('audit_logs', 'id_temp', new_column_name='id')
    op.alter_column('audit_logs', 'user_id_temp', new_column_name='user_id')
    op.alter_column('password_reset_tokens', 'id_temp', new_column_name='id')
    op.alter_column('password_reset_tokens', 'user_id_temp', new_column_name='user_id')
    
    # Step 7: Make UUID columns NOT NULL and set as primary keys
    op.alter_column('users', 'id', nullable=False)
    op.alter_column('orders', 'id', nullable=False)
    op.alter_column('orders', 'user_id', nullable=False)
    op.alter_column('songs', 'id', nullable=False)
    op.alter_column('songs', 'user_id', nullable=False)
    op.alter_column('songs', 'order_id', nullable=False)
    op.alter_column('song_images', 'id', nullable=False)
    op.alter_column('song_images', 'song_id', nullable=False)
    op.alter_column('feedback', 'id', nullable=False)
    op.alter_column('audit_logs', 'id', nullable=False)
    op.alter_column('password_reset_tokens', 'id', nullable=False)
    op.alter_column('password_reset_tokens', 'user_id', nullable=False)
    
    # Step 8: Add primary key constraints
    op.create_primary_key('users_pkey', 'users', ['id'])
    op.create_primary_key('orders_pkey', 'orders', ['id'])
    op.create_primary_key('songs_pkey', 'songs', ['id'])
    op.create_primary_key('song_images_pkey', 'song_images', ['id'])
    op.create_primary_key('feedback_pkey', 'feedback', ['id'])
    op.create_primary_key('audit_logs_pkey', 'audit_logs', ['id'])
    op.create_primary_key('password_reset_tokens_pkey', 'password_reset_tokens', ['id'])
    
    # Step 9: Recreate indexes with UUID columns
    # Users table indexes
    op.create_index('ix_users_id', 'users', ['id'])
    
    # Orders table indexes
    op.create_index('ix_orders_id', 'orders', ['id'])
    op.create_index('idx_orders_user_id_created_at', 'orders', ['user_id', 'created_at'])
    op.create_index('idx_orders_status_created_at', 'orders', ['status', 'created_at'])
    op.create_index('idx_orders_payment_provider_id', 'orders', ['payment_provider_id'])
    
    # Songs table indexes
    op.create_index('ix_songs_id', 'songs', ['id'])
    op.create_index('idx_songs_user_id_created_at', 'songs', ['user_id', 'created_at'])
    op.create_index('idx_songs_generation_status_created_at', 'songs', ['generation_status', 'created_at'])
    op.create_index('idx_songs_audio_status', 'songs', ['audio_status'])
    op.create_index('idx_songs_lyrics_status', 'songs', ['lyrics_status'])
    op.create_index('idx_songs_video_status', 'songs', ['video_status'])
    
    # Song images table indexes
    op.create_index('idx_song_images_song_id_order', 'song_images', ['song_id', 'order_index'])
    
    # Feedback table indexes
    op.create_index('ix_feedback_id', 'feedback', ['id'])
    op.create_index('idx_feedback_user_id', 'feedback', ['user_id'])
    op.create_index('idx_feedback_status_created_at', 'feedback', ['status', 'created_at'])
    
    # Audit logs table indexes
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    
    # Password reset tokens table indexes
    op.create_index('ix_password_reset_tokens_id', 'password_reset_tokens', ['id'])
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('idx_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])
    op.create_index('idx_password_reset_tokens_user_used', 'password_reset_tokens', ['user_id', 'used'])
    
    # Step 10: Recreate foreign key constraints
    op.create_foreign_key('orders_user_id_fkey', 'orders', 'users', ['user_id'], ['id'])
    op.create_foreign_key('songs_user_id_fkey', 'songs', 'users', ['user_id'], ['id'])
    op.create_foreign_key('songs_order_id_fkey', 'songs', 'orders', ['order_id'], ['id'])
    op.create_foreign_key('song_images_song_id_fkey', 'song_images', 'songs', ['song_id'], ['id'])
    op.create_foreign_key('feedback_user_id_fkey', 'feedback', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('audit_logs_user_id_fkey', 'audit_logs', 'users', ['user_id'], ['id'])
    op.create_foreign_key('password_reset_tokens_user_id_fkey', 'password_reset_tokens', 'users', ['user_id'], ['id'])


def downgrade():
    """Downgrade is not supported for this migration as it would cause data loss"""
    raise NotImplementedError("Downgrade from UUID to integer IDs is not supported") 