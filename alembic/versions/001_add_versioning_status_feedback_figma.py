"""add versioning status workflow feedback correction and figma integration

Revision ID: 001
Revises: 
Create Date: 2026-05-20 19:23:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Step 0: Add primary key to existing pepsi_translations table (if not exists)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_schema = 'customer_uat_ind' 
                    AND table_name = 'pepsi_translations' 
                    AND constraint_type = 'PRIMARY KEY'
            ) THEN
                ALTER TABLE customer_uat_ind.pepsi_translations 
                ADD CONSTRAINT pepsi_translations_pkey PRIMARY KEY (id);
            END IF;
        END $$;
    """)
    
    # Add status column to pepsi_translations (nullable first)
    op.add_column('pepsi_translations', sa.Column('status', sa.String(32), nullable=True), schema='customer_uat_ind')
    
    # Add Figma integration columns to pepsi_translations
    op.add_column('pepsi_translations', sa.Column('figma_node_id', sa.String(128), nullable=True), schema='customer_uat_ind')
    op.add_column('pepsi_translations', sa.Column('figma_file_key', sa.String(255), nullable=True), schema='customer_uat_ind')
    op.add_column('pepsi_translations', sa.Column('figma_screenshot_url', sa.Text(), nullable=True), schema='customer_uat_ind')
    
    # Add audit tracking columns to pepsi_translations
    op.add_column('pepsi_translations', sa.Column('created_by', sa.String(128), nullable=True), schema='customer_uat_ind')
    op.add_column('pepsi_translations', sa.Column('updated_by', sa.String(128), nullable=True), schema='customer_uat_ind')
    
    # Set default status for existing records to APPROVED
    op.execute("UPDATE customer_uat_ind.pepsi_translations SET status = 'APPROVED' WHERE status IS NULL")
    
    # Make status NOT NULL with default
    op.alter_column('pepsi_translations', 'status', nullable=False, server_default='PENDING_REVIEW', schema='customer_uat_ind')
    
    # Create check constraint for status values
    op.execute("""
        ALTER TABLE customer_uat_ind.pepsi_translations 
        ADD CONSTRAINT chk_status 
        CHECK (status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED'))
    """)
    
    # Create pepsi_translation_versions table
    op.execute("CREATE SEQUENCE IF NOT EXISTS customer_uat_ind.pepsi_translation_versions_id_seq")
    op.create_table(
        'pepsi_translation_versions',
        sa.Column('id', sa.BigInteger(), server_default=sa.text("nextval('customer_uat_ind.pepsi_translation_versions_id_seq')"), nullable=False),
        sa.Column('translation_id', sa.BigInteger(), nullable=False),
        sa.Column('label', sa.Text(), nullable=True),
        sa.Column('translation', sa.Text(), nullable=True),
        sa.Column('type', sa.String(255), nullable=True),
        sa.Column('status', sa.String(32), nullable=True),
        sa.Column('changed_by', sa.String(128), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['translation_id'], ['customer_uat_ind.pepsi_translations.id'], ),
        schema='customer_uat_ind'
    )
    op.execute("ALTER TABLE customer_uat_ind.pepsi_translation_versions ALTER COLUMN id SET NOT NULL")
    op.create_index(op.f('ix_pepsi_translation_versions_id'), 'pepsi_translation_versions', ['id'], unique=False, schema='customer_uat_ind')
    op.create_index(op.f('ix_pepsi_translation_versions_translation_id'), 'pepsi_translation_versions', ['translation_id'], unique=False, schema='customer_uat_ind')
    
    # Create pepsi_feedback_corrections table
    op.execute("CREATE SEQUENCE IF NOT EXISTS customer_uat_ind.pepsi_feedback_corrections_id_seq")
    op.create_table(
        'pepsi_feedback_corrections',
        sa.Column('id', sa.BigInteger(), server_default=sa.text("nextval('customer_uat_ind.pepsi_feedback_corrections_id_seq')"), nullable=False),
        sa.Column('translation_id', sa.BigInteger(), nullable=True),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('language_code', sa.String(10), nullable=False),
        sa.Column('ai_original_value', sa.Text(), nullable=True),
        sa.Column('corrected_value', sa.Text(), nullable=True),
        sa.Column('correction_reason', sa.Text(), nullable=True),
        sa.Column('corrected_by', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['translation_id'], ['customer_uat_ind.pepsi_translations.id'], ),
        schema='customer_uat_ind'
    )
    op.execute("ALTER TABLE customer_uat_ind.pepsi_feedback_corrections ALTER COLUMN id SET NOT NULL")
    op.create_index(op.f('ix_pepsi_feedback_corrections_id'), 'pepsi_feedback_corrections', ['id'], unique=False, schema='customer_uat_ind')
    op.create_index(op.f('ix_pepsi_feedback_corrections_language_code'), 'pepsi_feedback_corrections', ['language_code'], unique=False, schema='customer_uat_ind')


def downgrade():
    # Drop pepsi_feedback_corrections table
    op.drop_index(op.f('ix_pepsi_feedback_corrections_language_code'), table_name='pepsi_feedback_corrections', schema='customer_uat_ind')
    op.drop_index(op.f('ix_pepsi_feedback_corrections_id'), table_name='pepsi_feedback_corrections', schema='customer_uat_ind')
    op.drop_table('pepsi_feedback_corrections', schema='customer_uat_ind')
    op.execute("DROP SEQUENCE IF EXISTS customer_uat_ind.pepsi_feedback_corrections_id_seq")
    
    # Drop pepsi_translation_versions table
    op.drop_index(op.f('ix_pepsi_translation_versions_translation_id'), table_name='pepsi_translation_versions', schema='customer_uat_ind')
    op.drop_index(op.f('ix_pepsi_translation_versions_id'), table_name='pepsi_translation_versions', schema='customer_uat_ind')
    op.drop_table('pepsi_translation_versions', schema='customer_uat_ind')
    op.execute("DROP SEQUENCE IF EXISTS customer_uat_ind.pepsi_translation_versions_id_seq")
    
    # Drop check constraint
    op.execute("ALTER TABLE customer_uat_ind.pepsi_translations DROP CONSTRAINT IF EXISTS chk_status")
    
    # Drop columns from pepsi_translations
    op.drop_column('pepsi_translations', 'updated_by', schema='customer_uat_ind')
    op.drop_column('pepsi_translations', 'created_by', schema='customer_uat_ind')
    op.drop_column('pepsi_translations', 'figma_screenshot_url', schema='customer_uat_ind')
    op.drop_column('pepsi_translations', 'figma_file_key', schema='customer_uat_ind')
    op.drop_column('pepsi_translations', 'figma_node_id', schema='customer_uat_ind')
    op.drop_column('pepsi_translations', 'status', schema='customer_uat_ind')
