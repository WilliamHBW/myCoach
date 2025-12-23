"""
Vector Store - Storage and retrieval of vector embeddings using pgvector.
"""
import uuid
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import ContextEmbedding, ContentType
from app.services.context.embedding import EmbeddingService
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Vector storage and retrieval using pgvector."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
    
    async def store(
        self,
        content_text: str,
        content_type: str,
        plan_id: Optional[uuid.UUID] = None,
        metadata: Optional[dict] = None
    ) -> ContextEmbedding:
        """
        Store text content with its embedding.
        
        Args:
            content_text: Text content to store
            content_type: Type of content (plan/analysis/history)
            plan_id: Associated plan ID
            metadata: Additional metadata
            
        Returns:
            Created ContextEmbedding record
        """
        embedding = await self.embedding_service.generate_embedding(content_text)
        
        record = ContextEmbedding(
            plan_id=plan_id,
            content_type=content_type,
            content_text=content_text,
            embedding=embedding,
            metadata=metadata or {}
        )
        
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        
        logger.debug(
            "Stored embedding",
            id=str(record.id),
            content_type=content_type,
            plan_id=str(plan_id) if plan_id else None
        )
        
        return record
    
    async def search(
        self,
        query: str,
        plan_id: Optional[uuid.UUID] = None,
        content_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[ContextEmbedding]:
        """
        Search for similar content using vector similarity.
        
        Args:
            query: Query text to search for
            plan_id: Filter by plan ID
            content_types: Filter by content types
            limit: Maximum number of results
            
        Returns:
            List of matching ContextEmbedding records
        """
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        # Build query with filters
        stmt = select(ContextEmbedding)
        
        if plan_id:
            stmt = stmt.where(ContextEmbedding.plan_id == plan_id)
        
        if content_types:
            stmt = stmt.where(ContextEmbedding.content_type.in_(content_types))
        
        # Order by cosine similarity (using pgvector's <=> operator)
        stmt = stmt.order_by(
            ContextEmbedding.embedding.cosine_distance(query_embedding)
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        records = result.scalars().all()
        
        logger.debug(
            "Vector search completed",
            query_length=len(query),
            results_count=len(records),
            plan_id=str(plan_id) if plan_id else None
        )
        
        return list(records)
    
    async def get_by_plan(
        self,
        plan_id: uuid.UUID,
        content_types: Optional[List[str]] = None
    ) -> List[ContextEmbedding]:
        """
        Get all embeddings for a specific plan.
        
        Args:
            plan_id: Plan ID to filter by
            content_types: Filter by content types
            
        Returns:
            List of ContextEmbedding records
        """
        stmt = select(ContextEmbedding).where(
            ContextEmbedding.plan_id == plan_id
        ).order_by(ContextEmbedding.created_at.desc())
        
        if content_types:
            stmt = stmt.where(ContextEmbedding.content_type.in_(content_types))
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_by_plan(
        self,
        plan_id: uuid.UUID,
        content_types: Optional[List[str]] = None
    ) -> int:
        """
        Delete embeddings for a specific plan.
        
        Args:
            plan_id: Plan ID to delete
            content_types: Filter by content types
            
        Returns:
            Number of deleted records
        """
        stmt = delete(ContextEmbedding).where(
            ContextEmbedding.plan_id == plan_id
        )
        
        if content_types:
            stmt = stmt.where(ContextEmbedding.content_type.in_(content_types))
        
        result = await self.db.execute(stmt)
        
        logger.info(
            "Deleted embeddings",
            plan_id=str(plan_id),
            count=result.rowcount
        )
        
        return result.rowcount

