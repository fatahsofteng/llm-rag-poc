# RAG Pipeline POC - PostgreSQL + pgvector + pg_bigm

Proof of Concept for RAG (Retrieval Augmented Generation) pipeline using PostgreSQL with pgvector and pg_bigm extensions, following Epic requirements.

## Tech Stack

- **FastAPI** - REST API framework
- **PostgreSQL 15** - Primary database
- **pgvector** - Vector similarity search (cosine distance)
- **pg_bigm** - Full-text search with bigram indexing
- **Docker & Docker Compose** - Containerization

---

## Project Structure

```
llm-rag-poc/
├── README.md
├── .gitignore
├── Dockerfile                  # Custom PostgreSQL image with pgvector + pg_bigm
├── docker-compose.yml          # PostgreSQL service
├── requirements.txt
├── app/
│   └── main.py                # FastAPI application
└── migrations/
    └── 001_init.sql           # Database schema & extensions
```

---

## Quick Start

### 1. Prerequisites

- Docker Desktop
- Python 3.9+
- Git

### 2. Clone & Setup

#### Clone repository
```
git clone https://github.com/fatahsofteng/llm-rag-poc.git
cd llm-rag-poc
```

#### Create virtual environment
```
python -m venv venv
source venv/bin/activate  
# Windows: 
venv\Scripts\activate
```

# Install dependencies
```
pip install -r requirements.txt
```

### 3. Build & Start PostgreSQL

#### Build custom image (first time only, ~8-10 minutes)
```
docker-compose build
```

#### Start container
```
docker-compose up -d
```

#### Check logs
```
docker-compose logs -f postgres
```

#### Verify extensions installed
```
docker exec rag_postgres psql -U rag_user -d rag_db -c "\dx"
# Expected: vector, pg_bigm
```

### 4. Run FastAPI

```bash
python app/main.py
# Server running at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### 5. Test API

```bash
# Health check
curl http://localhost:8000/health

# Insert QA document (with channels & effective dates)
curl -X POST http://localhost:8000/ingest/fulltext \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "qa_col",
    "source_id": "qa_excel",
    "content": "How to transfer money via TWM mobile banking",
    "channels": ["TWM"],
    "action_code": "TRANSFER",
    "effective_from": "2024-01-01",
    "effective_to": "2025-12-31",
    "metadata": {"category": "banking"}
  }'

# Insert expired document (to test auto-filtering)
curl -X POST http://localhost:8000/ingest/fulltext \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "qa_col",
    "content": "Old expired promotion",
    "channels": ["TWM"],
    "effective_from": "2023-01-01",
    "effective_to": "2023-12-31"
  }'

# Search with filters
curl -X POST http://localhost:8000/search/fulltext \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transfer",
    "channels": ["TWM"],
    "limit": 20
  }'
# Expected: Only return valid documents (exclude expired)

# Get statistics
curl http://localhost:8000/stats
```

---

## Database Schema

### Tables

#### collections
Master table for metadata
- `collection_id` (PRIMARY KEY)
- `collection_name`, `description`
- `embedding_model_id`
- `group_id`, `channels[]`
- `metadata` (JSONB)
- Audit fields: `created_by`, `created_at`, `updated_by`, `updated_at`

#### vector_embeddings
Vector storage for semantic search
- `id` (PRIMARY KEY)
- `collection_id`, `source_id`, `knowledge_id`, `chunk_id`
- `channels[]` - CRITICAL: TWM/TDS filtering
- `action_code`, `build_id`
- `content`, `metadata` (JSONB)
- `embedding` VECTOR(1536)
- `effective_from`, `effective_to` - CRITICAL: QA date filtering
- Audit fields

#### fulltext_docs
Full-text search storage
- `id` (PRIMARY KEY)
- `collection_id`, `source_id`, `knowledge_id`, `chunk_id`
- `channels[]` - CRITICAL: TWM/TDS filtering
- `action_code`, `build_id`
- `content`, `metadata` (JSONB)
- `effective_from`, `effective_to` - CRITICAL: QA date filtering
- Audit fields

#### vector_tombstones & fulltext_deleted
Soft-delete tracking tables

### Indexes

- **IVFFlat** on `vector_embeddings.embedding` (cosine similarity)
- **GIN** on `fulltext_docs.content` (pg_bigm bigram index)
- **GIN** on metadata fields (attribute-based filtering)

---

## Key Features Implemented

### 1. pg_bigm Full-Text Search
- Bigram-based indexing for fuzzy matching
- Similarity scoring with `bigm_similarity()`
- Partial match and typo tolerance support

### 2. Channel Filtering (TWM/TDS)
- Array-based filtering: `channels && ['TWM']`
- Multi-channel query support

### 3. Date-Based Filtering (QA)
- Auto-exclude expired documents
- Filter by `effective_from` and `effective_to`

### 4. Audit Trail
- All tables include `created_by`, `created_at`, `updated_by`, `updated_at`

---

## Epic Alignment Status

### Implemented (Day 1)

**Story 1: PostgreSQL Extensions & Data Structures**
- pgvector extension enabled
- pg_bigm extension enabled and configured
- Complete schema with audit fields
- GIN indexes for metadata
- Tombstone tables for soft-delete

**Story 3: Full-text Adapter (Partial)**
- Basic fulltext insert endpoint
- pg_bigm search with similarity scoring
- Channel filtering
- Date-based filtering

### Not Yet Implemented (Day 2+)

**Story 2: Vector Store Adapter**
- Embedding generation (OpenAI/Azure/HuggingFace)
- Vector upsert endpoint
- Vector similarity search

**Story 4: Dynamic Embedding Provider**
- Multi-provider support (config-driven)
- Secret management integration

**Story 5: Search Service Integration**
- Hybrid search (RRF: vector + fulltext)
- Join with collections table
- Permission-based filtering

**Story 7: Airflow + Celery**
- DAG templates
- Celery workers and queues
- Config-driven pipeline (YAML)

**Story 8: Multi-Source Support**
- QA Excel parser (field validation)
- KM multi-format (Excel/PDF/TXT)
- Source adapters (S3/REST API)

**Story 9: Batch/Real-time Switching**
- StateStore versioning
- Build management
- Rollback capabilities

**Story 10: Multi-Tenant & Permissions**
- Group-based access control
- Permission checks in API layer

**Story 11: Airflow + Celery Infrastructure**
- CeleryExecutor configuration
- Queue mapping and worker deployment
- Monitoring (Flower/Prometheus)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/health` | Database health check |
| POST | `/ingest/fulltext` | Insert document (fulltext) |
| POST | `/search/fulltext` | Search with pg_bigm |
| GET | `/stats` | Database statistics |

---

## Configuration

### Environment Variables

Create `.env` file (optional):

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=rag_user
DB_PASS=rag_pass
DB_NAME=rag_db
```

### PostgreSQL Connection

Default DSN: `postgresql://rag_user:rag_pass@localhost:5432/rag_db`

---

## Development Notes

### pg_bigm vs pg_trgm

Epic requirement: **pg_bigm** (bigram indexing)
- Better for CJK languages
- 2-character sequences vs 3-character (trigram)
- Custom build required (not in default PostgreSQL)

### Similarity Threshold

```sql
SET pg_bigm.similarity_threshold = 0.3;
```

Range: 0.0 - 1.0 (lower = more fuzzy matching)

---

## Troubleshooting

### Container fails to start

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Extensions not found

```bash
docker exec rag_postgres psql -U rag_user -d rag_db -c "\dx"
```

Should display: `vector` and `pg_bigm`

### Search returns empty

Check:
1. Documents inserted? Run `curl http://localhost:8000/stats`
2. Date filtering? Update `effective_to` to future date
3. Channel filtering? Ensure channels match in query

### Build errors

```bash
# Clear Docker cache
docker system prune -a
docker volume prune

# Rebuild from scratch
docker-compose build --no-cache
```

---

## Business Context

### QA Pipeline (Structured Excel)

**Required Fields:**
- Knowledge ID, Category, Standard Question
- Guided Question, Customer Question
- Standard Answer, Short Message Content
- Action_Code, Effective Date, Expiration Date
- Response Channel (TWM/TDS)

**Key Features:**
- Auto-filter based on effective/expiry dates
- Channel-specific search

### KM Pipeline (General RAG)

**Supported Formats:**
- Excel, PDF, TXT

**Key Features:**
- Multi-format chunking
- Channel metadata extraction
- Standard RAG process

---

## Next Steps

### Day 2 Priorities
1. Vector embedding generation (OpenAI API)
2. Vector search endpoint
3. Hybrid search implementation (RRF)

### Future Enhancements
- Airflow DAG templates
- Multi-provider embeddings
- QA Excel parser with validation
- Multi-tenant permissions
- StateStore versioning
- Monitoring and observability

---

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [pg_bigm Documentation](https://github.com/pgbigm/pg_bigm)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- Epic Document: RAG Pipeline Migration (internal)

---

## License

Internal project

---

## Contact

**Developer:** Fatahillah

---

## Acknowledgments

This POC follows the Epic requirements for migrating RAG pipeline to PostgreSQL with pgvector and pg_bigm extensions, supporting dual-track content management (QA and KM) with channel-based filtering and date-based document lifecycle management.