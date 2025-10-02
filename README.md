# RAG Pipeline POC - PostgreSQL + pgvector + pg_bigm

Proof of Concept for RAG (Retrieval Augmented Generation) pipeline using PostgreSQL with pgvector and pg_bigm extensions, following Epic requirements.

## Tech Stack

- **FastAPI** - REST API framework
- **PostgreSQL 15** - Primary database
- **pgvector** - Vector similarity search (cosine distance)
- **pg_bigm** - Full-text search with bigram indexing
- **SQLModel** - SQL database ORM (Pydantic + SQLAlchemy)
- **Alembic** - Database migration tool
- **Docker & Docker Compose** - Containerization

---

## Project Structure

```
llm-rag-poc/
├── README.md
├── .env                        # Environment variables (not in git)
├── .env.example                # Environment template
├── .gitignore
├── Dockerfile                  # Custom PostgreSQL with pgvector + pg_bigm
├── docker-compose.yml
├── requirements.txt
├── alembic/
│   ├── env.py                  # Alembic configuration
│   └── versions/               # Migration files
│       └── xxxx_initial.py
├── alembic.ini
└── app/
    ├── main.py                 # FastAPI application
    ├── models.py               # SQLModel table definitions
    └── database.py             # Database connection
```

---

## Quick Start

### 1. Prerequisites

- Docker Desktop
- Python 3.9+
- Git

### 2. Clone & Setup

```bash
# Clone repository
git clone https://github.com/fatahsofteng/llm-rag-poc.git
cd llm-rag-poc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings (default values work for local development)
# DATABASE_URL=postgresql://rag_user:rag_pass@localhost:5432/rag_db
```

### 4. Build & Start PostgreSQL

```bash
# Build custom image (first time only, ~8-10 minutes)
docker-compose build

# Start container
docker-compose up -d

# Verify container running
docker-compose ps
# Expected: rag_postgres  Up (healthy)

# Check logs
docker-compose logs -f postgres
# Wait for "database system is ready to accept connections"
```

### 5. Run Database Migrations

```bash
# Run Alembic migrations (creates tables, indexes, extensions)
alembic upgrade head

# Verify tables created
docker exec rag_postgres psql -U rag_user -d rag_db -c "\dt"
# Expected: collections, vector_embeddings, fulltext_docs, vector_tombstones, fulltext_deleted

# Verify extensions
docker exec rag_postgres psql -U rag_user -d rag_db -c "\dx"
# Expected: vector, pg_bigm
```

### 6. Run FastAPI

```bash
# Run as module
python -m app.main

# API running at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 7. Test API

```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/

# Insert QA document
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

# Insert expired document (for testing auto-filter)
curl -X POST http://localhost:8000/ingest/fulltext \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "qa_col",
    "content": "Old expired promotion",
    "channels": ["TWM"],
    "effective_from": "2023-01-01",
    "effective_to": "2023-12-31"
  }'

# Search (will exclude expired documents automatically)
curl -X POST http://localhost:8000/search/fulltext \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transfer",
    "channels": ["TWM"],
    "limit": 20
  }'

# Get statistics
curl http://localhost:8000/stats
```

---

## Configuration

### Environment Variables

The application uses `.env` file for configuration. Never commit `.env` to git.

**Create from template:**
```bash
cp .env.example .env
```

**Available settings:**

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://rag_user:rag_pass@localhost:5432/rag_db` |
| `APP_HOST` | API server host | `0.0.0.0` |
| `APP_PORT` | API server port | `8000` |
| `APP_ENV` | Environment mode | `development` |

**Example `.env`:**
```env
DATABASE_URL=postgresql://rag_user:rag_pass@localhost:5432/rag_db
APP_HOST=0.0.0.0
APP_PORT=8000
APP_ENV=development
```

---

## Database Schema

### Tables

#### collections
Master table for metadata
- `collection_id` (PRIMARY KEY)
- `collection_name`, `description`
- `embedding_model_id`, `group_id`
- `channels[]` - Array for TWM/TDS filtering
- `metadata` (JSONB) - Flexible metadata storage
- Audit: `created_by`, `created_at`, `updated_by`, `updated_at`

#### vector_embeddings
Vector storage for semantic search
- `id` (BIGSERIAL PRIMARY KEY)
- `collection_id`, `source_id`, `knowledge_id`, `chunk_id`
- `channels[]` - **CRITICAL**: TWM/TDS filtering
- `action_code`, `build_id`
- `content`, `metadata` (JSONB)
- `embedding` VECTOR(1536) - pgvector type
- `effective_from`, `effective_to` - **CRITICAL**: QA date filtering
- Audit fields

#### fulltext_docs
Full-text search storage
- `id` (BIGSERIAL PRIMARY KEY)
- `collection_id`, `source_id`, `knowledge_id`, `chunk_id`
- `channels[]` - **CRITICAL**: TWM/TDS filtering
- `action_code`, `build_id`
- `content`, `metadata` (JSONB)
- `effective_from`, `effective_to` (DATE) - **CRITICAL**: QA filtering
- Audit fields

#### vector_tombstones & fulltext_deleted
Soft-delete tracking for data lifecycle management

### Indexes

- **IVFFlat** on `vector_embeddings.embedding` - Optimized vector similarity search
- **GIN** on `fulltext_docs.content` with `gin_bigm_ops` - Fast bigram matching
- **GIN** on all `metadata` columns - Flexible attribute filtering

---

## Key Features

### 1. SQLModel ORM
- Type-safe database models with Pydantic validation
- Automatic schema generation
- IDE autocomplete support
- Clean separation of concerns

### 2. Alembic Migrations
- Version-controlled schema changes
- Rollback capability: `alembic downgrade -1`
- Auto-generate migrations: `alembic revision --autogenerate`
- Migration history tracking

### 3. pg_bigm Full-Text Search
- Bigram-based indexing for fuzzy matching
- Similarity scoring with `bigm_similarity()`
- Typo tolerance and partial match support
- Better performance for CJK languages

### 4. Channel-Based Filtering
- Array overlap operator: `channels && ['TWM']`
- Multi-channel queries: `['TWM', 'TDS']`
- Business logic: Route queries to appropriate content

### 5. Date-Based Document Lifecycle
- Auto-exclude expired documents in QA search
- Effective date range validation
- Support for evergreen content (NULL dates)

### 6. Audit Trail
- Track who created/updated records
- Timestamp tracking for compliance
- Soft-delete with tombstone tables

---

## Day 2 Updates

### Migration from Day 1

**What Changed:**
- ✅ **Raw SQL → Alembic**: Version-controlled migrations instead of init script
- ✅ **psycopg2 → SQLModel**: Type-safe ORM with Pydantic validation
- ✅ **Manual exports → .env**: Environment-based configuration
- ✅ **Direct DB access → DAO pattern**: Cleaner architecture

**Benefits:**
- Better maintainability and code quality
- Easier schema evolution and rollbacks
- Type safety with IDE support
- Standard Python patterns (SQLModel + Alembic)

---

## Development Workflow

### Database Migrations

```bash
# Create new migration
alembic revision -m "add_new_column"

# Auto-generate from model changes
alembic revision --autogenerate -m "sync_models"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

### Running the Application

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
python -m app.main
```

### Testing

```bash
# API Documentation (interactive)
open http://localhost:8000/docs

# Health check
curl http://localhost:8000/health

# Check database stats
curl http://localhost:8000/stats
```

---

## Epic Alignment Status

### ✅ Implemented (Day 1-2)

**Story 1: PostgreSQL Extensions & Data Structures** - COMPLETE
- pgvector and pg_bigm extensions enabled
- Complete schema with all required fields
- GIN indexes on metadata for flexible filtering
- Tombstone tables for soft-delete
- Audit fields on all tables

**Story 3: Full-text Adapter** - BASIC
- Insert endpoint with SQLModel ORM
- pg_bigm search with similarity scoring
- Channel-based filtering
- Date-based filtering for QA
- Metadata support

### 🚧 Not Yet Implemented (Future)

**Story 2: Vector Store Adapter**
- Embedding generation (OpenAI/Azure/HuggingFace)
- Vector upsert operations
- Vector similarity search queries

**Story 4: Dynamic Embedding Provider**
- Multi-provider configuration
- Credential management
- Provider-specific parameters

**Story 5: Search Service Integration**
- Hybrid search (RRF algorithm)
- Collections table JOIN
- Permission-based filtering
- Weighted search scoring

**Story 7: Modular ETL Templates**
- Airflow DAG templates
- Task group patterns
- Adapter pattern examples

**Story 8: Multi-Source Support**
- QA Excel parser with validation
- KM multi-format handlers
- S3/GCS source adapters

**Story 9-11: Production Features**
- StateStore versioning
- Airflow + Celery infrastructure
- Multi-tenant permissions
- Monitoring (Flower/Prometheus)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint with version info |
| GET | `/health` | Database health check |
| GET | `/docs` | Interactive API documentation |
| POST | `/ingest/fulltext` | Insert document (SQLModel ORM) |
| POST | `/search/fulltext` | Search with pg_bigm + filters |
| GET | `/stats` | Database statistics |

---

## Troubleshooting

### Alembic migration fails

```bash
# Check current state
alembic current

# View pending migrations
alembic history

# Reset completely
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

### Container won't start

```bash
# Clean rebuild
docker-compose down -v
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

### Module import errors

```bash
# Always run as module from project root
python -m app.main

# Not: python app/main.py
```

### Database connection refused

```bash
# Verify container is running
docker-compose ps

# Check logs
docker-compose logs postgres

# Test connection
docker exec rag_postgres psql -U rag_user -d rag_db -c "SELECT 1"
```

### Search returns no results

**Check:**
1. Documents inserted? → `curl http://localhost:8000/stats`
2. Date filtering? → Ensure `effective_to` is in the future
3. Channel mismatch? → Verify channels in query match document
4. Extensions loaded? → `docker exec rag_postgres psql -U rag_user -d rag_db -c "\dx"`

---

## Business Context

### QA Pipeline (Structured Excel)

**Purpose:** Customer service knowledge base with strict lifecycle management

**Required Fields:**
- Knowledge ID, Category
- Standard Question, Guided Question, Customer Question
- Standard Answer, Short Message Content
- Action_Code
- Effective Date, Expiration Date
- Response Channel (TWM/TDS)

**Features:**
- Automatic expiration filtering
- Channel-specific routing
- Audit trail for compliance

### KM Pipeline (General RAG)

**Purpose:** General knowledge management with flexible content

**Supported Formats:**
- Excel spreadsheets
- PDF documents
- Text files

**Features:**
- Multi-format chunking
- Channel metadata extraction
- Standard RAG retrieval

---

## Performance Notes

### pg_bigm Index

- **Index type:** GIN with `gin_bigm_ops`
- **Size overhead:** ~2-3x larger than pg_trgm
- **Query speed:** Optimized for LIKE queries
- **Best for:** CJK languages, partial matches

### pgvector Index

- **Index type:** IVFFlat (Inverted File Flat)
- **Lists parameter:** 100 (for ~100K vectors)
- **Build time:** O(n) - created once
- **Query time:** Sub-linear with proper tuning

---

## Next Steps

### Immediate (Week 1)
1. Implement vector embedding generation
2. Add vector similarity search
3. Test with sample datasets

### Short-term (Month 1)
1. Hybrid search (RRF)
2. QA Excel parser
3. Basic Airflow DAG

### Long-term (Quarter 1)
1. Multi-provider embeddings
2. StateStore versioning
3. Multi-tenant permissions
4. Production monitoring

---

## References

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pg_bigm Documentation](https://github.com/pgbigm/pg_bigm)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- Epic: RAG Pipeline Migration (internal)

---

## License

Internal project

---

## Contact

**Developer:** Fatahillah  
**Repository:** https://github.com/fatahsofteng/llm-rag-poc

---

## Acknowledgments

This POC implements the foundational database layer for RAG pipeline migration, featuring PostgreSQL with pgvector for semantic search and pg_bigm for full-text search, managed through SQLModel ORM and Alembic migrations.