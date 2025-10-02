"""initial_schema_with_sqlmodel

Revision ID: 95d67896e540
Revises: 
Create Date: 2025-10-02 10:56:19.807195

"""
from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '95d67896e540'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions first
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_bigm')
    # op.execute("ALTER DATABASE rag_db SET pg_bigm.similarity_threshold = 0.3")
    
    # Tables
    op.create_table('collections',
        sa.Column('collection_id', sa.Text(), nullable=False),
        sa.Column('collection_name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('embedding_model_id', sa.Text(), nullable=False),
        sa.Column('group_id', sa.Text(), nullable=False),
        sa.Column('channels', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('created_by', sa.Text(), server_default='system', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('collection_id')
    )
    
    op.create_table('vector_embeddings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('collection_id', sa.Text(), nullable=False),
        sa.Column('source_id', sa.Text(), nullable=False),
        sa.Column('knowledge_id', sa.Text(), nullable=True),
        sa.Column('chunk_id', sa.Text(), nullable=False),
        sa.Column('channels', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('action_code', sa.Text(), nullable=True),
        sa.Column('build_id', sa.Text(), server_default='build_0', nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('effective_from', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('effective_to', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_by', sa.Text(), server_default='system', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('fulltext_docs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('collection_id', sa.Text(), nullable=False),
        sa.Column('source_id', sa.Text(), nullable=False),
        sa.Column('knowledge_id', sa.Text(), nullable=True),
        sa.Column('chunk_id', sa.Text(), nullable=False),
        sa.Column('channels', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('action_code', sa.Text(), nullable=True),
        sa.Column('build_id', sa.Text(), server_default='build_0', nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_by', sa.Text(), server_default='system', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('vector_tombstones',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('collection_id', sa.Text(), nullable=False),
        sa.Column('chunk_id', sa.Text(), nullable=False),
        sa.Column('deleted_by', sa.Text(), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('fulltext_deleted',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('collection_id', sa.Text(), nullable=False),
        sa.Column('chunk_id', sa.Text(), nullable=False),
        sa.Column('deleted_by', sa.Text(), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes
    op.execute("""
        CREATE INDEX vector_embeddings_ivfflat 
        ON vector_embeddings 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    """)
    op.create_index('vector_embeddings_metadata_gin', 'vector_embeddings', ['metadata'], 
                    unique=False, postgresql_using='gin')
    
    op.execute("""
        CREATE INDEX fulltext_docs_bigm 
        ON fulltext_docs 
        USING gin (content gin_bigm_ops)
    """)
    op.create_index('fulltext_docs_metadata_gin', 'fulltext_docs', ['metadata'], 
                    unique=False, postgresql_using='gin')
    op.create_index('collections_metadata_gin', 'collections', ['metadata'], 
                    unique=False, postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('collections_metadata_gin', table_name='collections')
    op.drop_index('fulltext_docs_metadata_gin', table_name='fulltext_docs')
    op.execute('DROP INDEX IF EXISTS fulltext_docs_bigm')
    op.drop_index('vector_embeddings_metadata_gin', table_name='vector_embeddings')
    op.execute('DROP INDEX IF EXISTS vector_embeddings_ivfflat')
    
    op.drop_table('fulltext_deleted')
    op.drop_table('vector_tombstones')
    op.drop_table('fulltext_docs')
    op.drop_table('vector_embeddings')
    op.drop_table('collections')
    
    op.execute('DROP EXTENSION IF EXISTS pg_bigm CASCADE')
    op.execute('DROP EXTENSION IF EXISTS vector CASCADE')
