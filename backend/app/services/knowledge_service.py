# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/knowledge_service.py

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def retrieve_knowledge(db: Session, roles: list[str], query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve active knowledge entries scoped to the user's database roles."""
    if not roles or not query.strip():
        return []

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
        {"title": row.title, "department": row.department, "content": row.content, "source": row.source}
        for row in result.fetchall()
    ]