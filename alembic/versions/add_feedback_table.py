"""add_feedback_table

Revision ID: add_feedback_table
Revises: e386d9925d7f
Create Date: 2025-07-11 09:27:59.340154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_feedback_table'
down_revision: Union[str, None] = 'e386d9925d7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create feedback table
    op.create_table('feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),  # Allow null for anonymous feedback
        sa.Column('email', sa.String(length=255), nullable=True),  # For anonymous users
        sa.Column('name', sa.String(length=255), nullable=True),  # For anonymous users
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='general'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)
    op.create_index('idx_feedback_status_created_at', 'feedback', ['status', 'created_at'], unique=False)
    op.create_index('idx_feedback_user_id', 'feedback', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop feedback table
    op.drop_index('idx_feedback_user_id', table_name='feedback')
    op.drop_index('idx_feedback_status_created_at', table_name='feedback')
    op.drop_index(op.f('ix_feedback_id'), table_name='feedback')
    op.drop_table('feedback') 