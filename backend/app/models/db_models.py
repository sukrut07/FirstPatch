"""
FirstPatch AI — SQLAlchemy 2.x ORM Models (Database Tables)
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RepositoryCache(Base):
    """Cached repository analysis results."""
    __tablename__ = "repository_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    analysis_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)


class ContributionSession(Base):
    """Records the contribution journey for a user/repo/issue combination."""
    __tablename__ = "contribution_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IssueCache(Base):
    """Cached GitHub issue lists."""
    __tablename__ = "issue_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    issues_data: Mapped[list] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
