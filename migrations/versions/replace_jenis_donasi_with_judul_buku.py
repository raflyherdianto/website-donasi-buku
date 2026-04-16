"""Replace jenis_donasi with judul_buku in detail_donasi table

Revision ID: replace_jenis_judul
Revises: add_jenis_donasi
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'replace_jenis_judul'
down_revision = 'add_jenis_donasi'
branch_labels = None
depends_on = None


def upgrade():
    # Add judul_buku column
    op.add_column('detail_donasi', sa.Column('judul_buku', sa.String(255), nullable=True))
    
    # Remove jenis_donasi column
    op.drop_column('detail_donasi', 'jenis_donasi')


def downgrade():
    # Add jenis_donasi column back
    op.add_column('detail_donasi', sa.Column('jenis_donasi', sa.String(50), nullable=True))
    
    # Remove judul_buku column
    op.drop_column('detail_donasi', 'judul_buku')
