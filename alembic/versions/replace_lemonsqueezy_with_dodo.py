"""Replace LemonSqueezy fields with Dodo Payments fields

Revision ID: replace_lemonsqueezy_with_dodo
Revises: convert_ids_to_uuid
Create Date: 2025-01-07 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'replace_lemonsqueezy_with_dodo'
down_revision = 'convert_ids_to_uuid'
branch_labels = None
depends_on = None


def upgrade():
    """Replace LemonSqueezy columns with Dodo Payments columns"""
    
    # Drop existing unique constraints on LemonSqueezy fields
    op.drop_constraint('orders_lemon_squeezy_order_id_key', 'orders', type_='unique')
    op.drop_constraint('orders_lemon_squeezy_payment_id_key', 'orders', type_='unique')
    
    # Add new Dodo payment columns
    op.add_column('orders', sa.Column('dodo_order_id', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('dodo_payment_id', sa.String(), nullable=True))
    
    # Copy data from old columns to new columns (if any data exists)
    op.execute('UPDATE orders SET dodo_order_id = lemon_squeezy_order_id WHERE lemon_squeezy_order_id IS NOT NULL')
    op.execute('UPDATE orders SET dodo_payment_id = lemon_squeezy_payment_id WHERE lemon_squeezy_payment_id IS NOT NULL')
    
    # Drop old LemonSqueezy columns
    op.drop_column('orders', 'lemon_squeezy_order_id')
    op.drop_column('orders', 'lemon_squeezy_payment_id')
    
    # Add unique constraints on new Dodo columns
    op.create_unique_constraint('orders_dodo_order_id_key', 'orders', ['dodo_order_id'])
    op.create_unique_constraint('orders_dodo_payment_id_key', 'orders', ['dodo_payment_id'])


def downgrade():
    """Downgrade back to LemonSqueezy fields"""
    
    # Drop Dodo constraints
    op.drop_constraint('orders_dodo_order_id_key', 'orders', type_='unique')
    op.drop_constraint('orders_dodo_payment_id_key', 'orders', type_='unique')
    
    # Add back LemonSqueezy columns
    op.add_column('orders', sa.Column('lemon_squeezy_order_id', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('lemon_squeezy_payment_id', sa.String(), nullable=True))
    
    # Copy data back (if any)
    op.execute('UPDATE orders SET lemon_squeezy_order_id = dodo_order_id WHERE dodo_order_id IS NOT NULL')
    op.execute('UPDATE orders SET lemon_squeezy_payment_id = dodo_payment_id WHERE dodo_payment_id IS NOT NULL')
    
    # Drop Dodo columns
    op.drop_column('orders', 'dodo_order_id')
    op.drop_column('orders', 'dodo_payment_id')
    
    # Recreate LemonSqueezy constraints
    op.create_unique_constraint('orders_lemon_squeezy_order_id_key', 'orders', ['lemon_squeezy_order_id'])
    op.create_unique_constraint('orders_lemon_squeezy_payment_id_key', 'orders', ['lemon_squeezy_payment_id']) 