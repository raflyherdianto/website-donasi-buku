"""add jenis_donasi column to detail_donasi

Revision ID: add_jenis_donasi
Revises: 59b4f0b9be31
Create Date: 2025-12-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_jenis_donasi'
down_revision = '59b4f0b9be31'
branch_labels = None
depends_on = None


def upgrade():
    # Add jenis_donasi column to detail_donasi table
    op.add_column('detail_donasi', sa.Column('jenis_donasi', sa.String(50), nullable=True))


def downgrade():
    # Remove jenis_donasi column from detail_donasi table
    op.drop_column('detail_donasi', 'jenis_donasi')
