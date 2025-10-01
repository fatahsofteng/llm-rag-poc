from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Optional
import json

app = FastAPI(title="RAG POC", version="0.1.0")

# Database connection
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "rag_user"),
        password=os.getenv("DB_PASS", "rag_pass"),
        database=os.getenv("DB_NAME", "rag_db")
    )

# Pydantic models
class Document(BaseModel):
    collection_id: str
    source_id: str = "default_source"
    knowledge_id: Optional[str] = None
    content: str
    channels: List[str] = ["TWM"]  # TWM, TDS, or both
    action_code: Optional[str] = None
    effective_from: Optional[str] = None  # ISO format: 2024-01-01
    effective_to: Optional[str] = None
    metadata: Optional[dict] = {}

class SearchQuery(BaseModel):
    query: str
    collection_id: Optional[str] = None
    channels: List[str] = []  # Filter by channels: TWM, TDS
    search_type: str = "fulltext"  # fulltext, vector, hybrid
    limit: int = 20  # Epic requirement: top 20 results

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: dict

@app.get("/")
def root():
    return {"message": "RAG POC API", "status": "running"}

@app.get("/health")
def health_check():
    """Check database connection"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

@app.post("/ingest/fulltext")
def ingest_fulltext(doc: Document):
    """Insert document into full-text search table"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        chunk_id = f"{doc.collection_id}_{hash(doc.content) % 10000}"
        build_id = "build_0"  # In production, this comes from Airflow DAG
        
        cursor.execute("""
            INSERT INTO fulltext_docs (
                collection_id, source_id, knowledge_id, chunk_id, 
                channels, action_code, build_id, content, metadata,
                effective_from, effective_to, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            doc.collection_id, doc.source_id, doc.knowledge_id, chunk_id,
            doc.channels, doc.action_code, build_id, doc.content, 
            json.dumps(doc.metadata),
            doc.effective_from, doc.effective_to, 'api_user'
        ))
        
        result_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"status": "success", "id": result_id, "chunk_id": chunk_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/fulltext", response_model=List[SearchResult])
def search_fulltext(query: SearchQuery):
    """Full-text search using pg_bigm with channel & date filtering"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Enable pg_bigm similarity for this session
        cursor.execute("SET pg_bigm.similarity_threshold = 0.3;")
        
        # Base query with pg_bigm similarity
        sql = """
            SELECT 
                f.chunk_id,
                f.content,
                f.metadata,
                f.channels,
                f.effective_from,
                f.effective_to,
                bigm_similarity(f.content, %s) as score
            FROM fulltext_docs f
            WHERE f.content LIKE %s
        """
        params = [query.query, f"%{query.query}%"]
        
        # Filter by collection
        if query.collection_id:
            sql += " AND f.collection_id = %s"
            params.append(query.collection_id)
        
        # CRITICAL: Filter by channels (TWM, TDS)
        if query.channels:
            sql += " AND f.channels && %s"
            params.append(query.channels)
        
        # CRITICAL: QA filtering - exclude expired documents
        sql += """
            AND (
                f.effective_from IS NULL 
                OR f.effective_from <= CURRENT_DATE
            )
            AND (
                f.effective_to IS NULL 
                OR f.effective_to >= CURRENT_DATE
            )
        """
        
        sql += " ORDER BY score DESC LIMIT %s"
        params.append(query.limit)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [
            SearchResult(
                chunk_id=r['chunk_id'],
                content=r['content'],
                score=float(r['score']) if r['score'] else 0.0,
                metadata=r['metadata'] or {}
            )
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/stats")
def get_stats():
    """Get database statistics"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM fulltext_docs")
        fulltext_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vector_embeddings")
        vector_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            "fulltext_docs": fulltext_count,
            "vector_embeddings": vector_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)