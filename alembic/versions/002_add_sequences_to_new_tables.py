"""Add sequences to new tables for auto-increment

Revision ID: 002
Revises: 001
Create Date: 2026-05-20 17:47:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create sequence for pepsi_translation_versions
    op.execute("CREATE SEQUENCE IF NOT EXISTS customer_uat_ind.pepsi_translation_versions_id_seq")
    op.execute("""
        ALTER TABLE customer_uat_ind.pepsi_translation_versions 
        ALTER COLUMN id SET DEFAULT nextval('customer_uat_ind.pepsi_translation_versions_id_seq')
    """)
    op.execute("ALTER TABLE customer_uat_ind.pepsi_translation_versions ALTER COLUMN id SET NOT NULL")
    
    # Create sequence for pepsi_feedback_corrections
    op.execute("CREATE SEQUENCE IF NOT EXISTS customer_uat_ind.pepsi_feedback_corrections_id_seq")
    op.execute("""
        ALTER TABLE customer_uat_ind.pepsi_feedback_corrections 
        ALTER COLUMN id SET DEFAULT nextval('customer_uat_ind.pepsi_feedback_corrections_id_seq')
    """)
    op.execute("ALTER TABLE customer_uat_ind.pepsi_feedback_corrections ALTER COLUMN id SET NOT NULL")


def downgrade():
    # Remove sequence from pepsi_translation_versions
    op.execute("ALTER TABLE customer_uat_ind.pepsi_translation_versions ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS customer_uat_ind.pepsi_translation_versions_id_seq")
    
    # Remove sequence from pepsi_feedback_corrections
    op.execute("ALTER TABLE customer_uat_ind.pepsi_feedback_corrections ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS customer_uat_ind.pepsi_feedback_corrections_id_seq")
