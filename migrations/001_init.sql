-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_bigm;

-- Configure pg_bigm
ALTER DATABASE rag_db SET pg_bigm.similarity_threshold = 0.3;

-- Collections master table (REQUIRED for join search results)
CREATE TABLE IF NOT EXISTS collections (
    collection_id TEXT PRIMARY KEY,
    collection_name TEXT NOT NULL,
    description TEXT,
    embedding_model_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    channels TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by TEXT NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_by TEXT,
    updated_at TIMESTAMPTZ
);

-- Vector embeddings table
CREATE TABLE IF NOT EXISTS vector_embeddings (
    id BIGSERIAL PRIMARY KEY,
    collection_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    knowledge_id TEXT,
    chunk_id TEXT NOT NULL,
    channels TEXT[] NOT NULL DEFAULT '{}',  -- CRITICAL: for TWM/TDS filtering
    action_code TEXT,
    build_id TEXT NOT NULL DEFAULT 'build_0',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding VECTOR(1536) NOT NULL,
    effective_from TIMESTAMPTZ,  -- CRITICAL: for QA filtering
    effective_to TIMESTAMPTZ,    -- CRITICAL: for QA filtering
    created_by TEXT NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_by TEXT,
    updated_at TIMESTAMPTZ
);

-- Create vector index (IVFFlat for similarity search)
CREATE INDEX IF NOT EXISTS vector_embeddings_ivfflat 
ON vector_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Full-text search table
CREATE TABLE IF NOT EXISTS fulltext_docs (
    id BIGSERIAL PRIMARY KEY,
    collection_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    knowledge_id TEXT,
    chunk_id TEXT NOT NULL,
    channels TEXT[] NOT NULL DEFAULT '{}',  -- CRITICAL: for TWM/TDS filtering
    action_code TEXT,
    build_id TEXT NOT NULL DEFAULT 'build_0',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    effective_from DATE,      -- CRITICAL: for QA filtering
    effective_to DATE,        -- CRITICAL: for QA filtering
    created_by TEXT NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_by TEXT,
    updated_at TIMESTAMPTZ
);

-- Create bigram index for full-text search
CREATE INDEX IF NOT EXISTS fulltext_docs_bigm 
ON fulltext_docs 
USING gin (content gin_bigm_ops);

-- Metadata index (optional, for filtering)
CREATE INDEX IF NOT EXISTS vector_embeddings_metadata_gin 
ON vector_embeddings 
USING gin (metadata);

CREATE INDEX IF NOT EXISTS fulltext_docs_metadata_gin 
ON fulltext_docs 
USING gin (metadata);

-- Collections metadata index
CREATE INDEX IF NOT EXISTS collections_metadata_gin 
ON collections 
USING gin (metadata);

-- Tombstone tables (for soft-delete)
CREATE TABLE IF NOT EXISTS vector_tombstones (
    id BIGSERIAL PRIMARY KEY,
    collection_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    deleted_by TEXT NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fulltext_deleted (
    id BIGSERIAL PRIMARY KEY,
    collection_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    deleted_by TEXT NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT now()
);