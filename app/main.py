from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select, text
from typing import List, Optional
from datetime import date, datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from .database import get_session
from .models import FulltextDocs, VectorEmbeddings
from pydantic import BaseModel

app = FastAPI(title="RAG POC with SQLModel", version="0.2.0")

# Request/Response models
class DocumentCreate(BaseModel):
    collection_id: str
    source_id: str = "default_source"
    knowledge_id: Optional[str] = None
    content: str
    channels: List[str] = ["TWM"]
    action_code: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    metadata: Optional[dict] = {}

class SearchQuery(BaseModel):
    query: str
    collection_id: Optional[str] = None
    channels: List[str] = []
    search_type: str = "fulltext"
    limit: int = 20

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: dict

@app.get("/")
def root():
    return {"message": "RAG POC API with SQLModel", "status": "running", "version": "0.2.0"}

@app.get("/health")
def health_check(session: Session = Depends(get_session)):
    """Check database connection"""
    try:
        session.exec(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

@app.post("/ingest/fulltext")
def ingest_fulltext(doc: DocumentCreate, session: Session = Depends(get_session)):
    """Insert document into full-text search table using SQLModel"""
    try:
        chunk_id = f"{doc.collection_id}_{hash(doc.content) % 10000}"
        
        # Parse dates
        effective_from = date.fromisoformat(doc.effective_from) if doc.effective_from else None
        effective_to = date.fromisoformat(doc.effective_to) if doc.effective_to else None
        
        db_doc = FulltextDocs(
            collection_id=doc.collection_id,
            source_id=doc.source_id,
            knowledge_id=doc.knowledge_id,
            chunk_id=chunk_id,
            channels=doc.channels,
            action_code=doc.action_code,
            content=doc.content,
            meta=doc.metadata or {},  # Changed: metadata → meta
            effective_from=effective_from,
            effective_to=effective_to,
            created_by="api_user"
        )
        
        session.add(db_doc)
        session.commit()
        session.refresh(db_doc)
        
        return {"status": "success", "id": db_doc.id, "chunk_id": chunk_id}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/fulltext", response_model=List[SearchResult])
def search_fulltext(query: SearchQuery, session: Session = Depends(get_session)):
    """Full-text search using pg_bigm with SQLModel"""
    try:
        # Use raw SQL for complex query with pg_bigm
        sql = text("""
            SELECT 
                chunk_id,
                content,
                metadata,
                bigm_similarity(content, :query) as score
            FROM fulltext_docs
            WHERE content LIKE :like_query
        """)
        
        params = {"query": query.query, "like_query": f"%{query.query}%"}
        
        # Build dynamic filters
        filters = []
        if query.collection_id:
            filters.append("collection_id = :collection_id")
            params["collection_id"] = query.collection_id
        
        if query.channels:
            filters.append("channels && :channels")
            params["channels"] = query.channels
        
        # Date filtering
        filters.append("(effective_from IS NULL OR effective_from <= CURRENT_DATE)")
        filters.append("(effective_to IS NULL OR effective_to >= CURRENT_DATE)")
        
        # Combine filters
        if filters:
            sql = text(str(sql) + " AND " + " AND ".join(filters) + " ORDER BY score DESC LIMIT :limit")
        
        params["limit"] = query.limit
        
        # Bind parameters
        sql = sql.bindparams(**params)
        
        results = session.exec(sql).all()
        
        return [
            SearchResult(
                chunk_id=row[0],
                content=row[1],
                score=float(row[3]) if row[3] else 0.0,
                metadata=row[2] or {}
            )
            for row in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/stats")
def get_stats(session: Session = Depends(get_session)):
    """Get database statistics using SQLModel"""
    try:
        fulltext_count = len(session.exec(select(FulltextDocs)).all())
        vector_count = len(session.exec(select(VectorEmbeddings)).all())
        
        return {
            "fulltext_docs": fulltext_count,
            "vector_embeddings": vector_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000))
    )