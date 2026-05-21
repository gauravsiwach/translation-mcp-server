"""Add version column to pepsi_translations

Revision ID: 003
Revises: 002
Create Date: 2026-05-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add version column to pepsi_translations
    op.add_column('pepsi_translations', sa.Column('version', sa.BigInteger(), nullable=True), schema='customer_uat_ind')
    
    # Add primary key constraint to pepsi_translation_versions (if not exists)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_schema = 'customer_uat_ind' 
                    AND table_name = 'pepsi_translation_versions' 
                    AND constraint_type = 'PRIMARY KEY'
            ) THEN
                ALTER TABLE customer_uat_ind.pepsi_translation_versions 
                ADD CONSTRAINT pepsi_translation_versions_pkey PRIMARY KEY (id);
            END IF;
        END $$;
    """)
    
    # Add foreign key constraint
    op.execute("""
        ALTER TABLE customer_uat_ind.pepsi_translations 
        ADD CONSTRAINT fk_pepsi_translations_version 
        FOREIGN KEY (version) REFERENCES customer_uat_ind.pepsi_translation_versions(id)
    """)


def downgrade():
    # Remove foreign key constraint
    op.execute("""
        ALTER TABLE customer_uat_ind.pepsi_translations 
        DROP CONSTRAINT IF EXISTS fk_pepsi_translations_version
    """)
    
    # Remove version column
    op.drop_column('pepsi_translations', 'version', schema='customer_uat_ind')
