# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/knowledge_service.py

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.services.embedding_service import embedding_service


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"

logger = logging.getLogger(__name__)


async def retrieve_knowledge(db: Session, roles: list[str], query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve role-scoped knowledge semantically, with full-text fallback."""
    if not roles or not query.strip():
        return []

    if embedding_service.enabled:
        try:
            embedding = await embedding_service.embed(query)
            result = db.execute(
                text("""
                    select title, department, content, source, metadata, similarity
                    from match_knowledge_documents(cast(:query_embedding as extensions.vector), :roles, :limit)
                """),
                {"query_embedding": _vector_literal(embedding), "roles": roles, "limit": limit},
            )
            return [
                {"title": row.title, "department": row.department, "content": row.content,
                 "source": row.source, "metadata": row.metadata, "similarity": row.similarity}
                for row in result.fetchall()
            ]
        except Exception:
            logger.exception("Semantic knowledge retrieval failed; using full-text fallback")

    result = db.execute(
        text("""
            select title, department, content, source
            from knowledge_documents
            where is_active = true
              and department = any(:roles)
              and to_tsvector('english', title || ' ' || content)
                  @@ plainto_tsquery('english', :query)
            order by ts_rank(
                to_tsvector('english', title || ' ' || content),
                plainto_tsquery('english', :query)
            ) desc
            limit :limit
        """),
        {"roles": roles, "query": query, "limit": limit},
    )
    return [
        {"title": row.title, "department": row.department, "content": row.content, "source": row.source, "similarity": None}
        for row in result.fetchall()
    ]