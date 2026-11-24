"""add landmark precedents table

Revision ID: a1b2c3d4e5f6
Revises: 137b7ec3d32e
Create Date: 2026-11-24 13:22:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '137b7ec3d32e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'landmark_precedents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('citation', sa.String(), nullable=False),
        sa.Column('court', sa.String(), server_default='Supreme Court of India', nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('bench', sa.String(), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('sections_invoked', sa.String(), nullable=True),
        sa.Column('ratio_decidendi', sa.Text(), nullable=False),
        sa.Column('facts_summary', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_landmark_precedents_id'), 'landmark_precedents', ['id'], unique=False)
    op.create_index(op.f('ix_landmark_precedents_title'), 'landmark_precedents', ['title'], unique=False)
    op.create_index(op.f('ix_landmark_precedents_citation'), 'landmark_precedents', ['citation'], unique=False)
    op.create_index(op.f('ix_landmark_precedents_subject'), 'landmark_precedents', ['subject'], unique=False)
    op.create_index(op.f('ix_landmark_precedents_year'), 'landmark_precedents', ['year'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_landmark_precedents_year'), table_name='landmark_precedents')
    op.drop_index(op.f('ix_landmark_precedents_subject'), table_name='landmark_precedents')
    op.drop_index(op.f('ix_landmark_precedents_citation'), table_name='landmark_precedents')
    op.drop_index(op.f('ix_landmark_precedents_title'), table_name='landmark_precedents')
    op.drop_index(op.f('ix_landmark_precedents_id'), table_name='landmark_precedents')
    op.drop_table('landmark_precedents')
