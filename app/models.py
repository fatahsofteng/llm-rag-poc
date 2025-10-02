from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy import Text
from pgvector.sqlalchemy import Vector
from typing import Optional, List
from datetime import datetime, date

class Collections(SQLModel, table=True):
    __tablename__ = "collections"
    
    collection_id: str = Field(sa_column=Column(Text, primary_key=True))
    collection_name: str = Field(sa_column=Column(Text, nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    embedding_model_id: str = Field(sa_column=Column(Text, nullable=False))
    group_id: str = Field(sa_column=Column(Text, nullable=False))
    channels: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(Text), server_default="{}"))
    meta: dict = Field(default_factory=dict, sa_column=Column("metadata", JSONB, server_default="{}"))  # Renamed field, same column
    created_by: str = Field(default="system", sa_column=Column(Text, nullable=False, server_default="system"))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column("created_at", nullable=False, server_default="now()"))
    updated_by: Optional[str] = Field(default=None, sa_column=Column(Text))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column("updated_at"))


class VectorEmbeddings(SQLModel, table=True):
    __tablename__ = "vector_embeddings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: str = Field(sa_column=Column(Text, nullable=False))
    source_id: str = Field(sa_column=Column(Text, nullable=False))
    knowledge_id: Optional[str] = Field(default=None, sa_column=Column(Text))
    chunk_id: str = Field(sa_column=Column(Text, nullable=False))
    channels: List[str] = Field(sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"))
    action_code: Optional[str] = Field(default=None, sa_column=Column(Text))
    build_id: str = Field(default="build_0", sa_column=Column(Text, nullable=False, server_default="build_0"))
    content: str = Field(sa_column=Column(Text, nullable=False))
    meta: dict = Field(default_factory=dict, sa_column=Column("metadata", JSONB, server_default="{}"))
    embedding: List[float] = Field(sa_column=Column(Vector(1536), nullable=False))
    effective_from: Optional[datetime] = Field(default=None)
    effective_to: Optional[datetime] = Field(default=None)
    created_by: str = Field(default="system", sa_column=Column(Text, nullable=False, server_default="system"))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column("created_at", nullable=False, server_default="now()"))
    updated_by: Optional[str] = Field(default=None, sa_column=Column(Text))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column("updated_at"))


class FulltextDocs(SQLModel, table=True):
    __tablename__ = "fulltext_docs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: str = Field(sa_column=Column(Text, nullable=False))
    source_id: str = Field(sa_column=Column(Text, nullable=False))
    knowledge_id: Optional[str] = Field(default=None, sa_column=Column(Text))
    chunk_id: str = Field(sa_column=Column(Text, nullable=False))
    channels: List[str] = Field(sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"))
    action_code: Optional[str] = Field(default=None, sa_column=Column(Text))
    build_id: str = Field(default="build_0", sa_column=Column(Text, nullable=False, server_default="build_0"))
    content: str = Field(sa_column=Column(Text, nullable=False))
    meta: dict = Field(default_factory=dict, sa_column=Column("metadata", JSONB, server_default="{}"))
    effective_from: Optional[date] = Field(default=None)
    effective_to: Optional[date] = Field(default=None)
    created_by: str = Field(default="system", sa_column=Column(Text, nullable=False, server_default="system"))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column("created_at", nullable=False, server_default="now()"))
    updated_by: Optional[str] = Field(default=None, sa_column=Column(Text))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column("updated_at"))


class VectorTombstones(SQLModel, table=True):
    __tablename__ = "vector_tombstones"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: str = Field(sa_column=Column(Text, nullable=False))
    chunk_id: str = Field(sa_column=Column(Text, nullable=False))
    deleted_by: str = Field(sa_column=Column(Text, nullable=False))
    deleted_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column("deleted_at", nullable=False, server_default="now()"))


class FulltextDeleted(SQLModel, table=True):
    __tablename__ = "fulltext_deleted"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: str = Field(sa_column=Column(Text, nullable=False))
    chunk_id: str = Field(sa_column=Column(Text, nullable=False))
    deleted_by: str = Field(sa_column=Column(Text, nullable=False))
    deleted_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column("deleted_at", nullable=False, server_default="now()"))