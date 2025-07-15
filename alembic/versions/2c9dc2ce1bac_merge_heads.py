"""merge_heads

Revision ID: 2c9dc2ce1bac
Revises: replace_lemonsqueezy_with_dodo, add_feedback_table
Create Date: 2025-07-15 08:56:35.195137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c9dc2ce1bac'
down_revision: Union[str, None] = ('replace_lemonsqueezy_with_dodo', 'add_feedback_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
