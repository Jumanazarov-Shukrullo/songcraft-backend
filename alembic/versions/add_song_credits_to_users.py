"""add_song_credits_to_users

Revision ID: add_song_credits_001
Revises: 2c9dc2ce1bac
Create Date: 2025-07-15 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_song_credits_001'
down_revision: Union[str, None] = '2c9dc2ce1bac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add song_credits column to users table
    op.add_column('users', sa.Column('song_credits', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove song_credits column from users table
    op.drop_column('users', 'song_credits') 