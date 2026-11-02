# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/ghl_contact_sync_state.py
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GHLContactSyncState(Base):
    __tablename__ = "ghl_contact_sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    cursor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    cursor_after: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="idle")
    cycle_cutoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contacts_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contacts_queued: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
