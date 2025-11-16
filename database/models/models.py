import enum
from typing import List, Optional
from sqlalchemy import String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime


class Base(AsyncAttrs, DeclarativeBase):
    __mapper_args__ = {'eager_defaults': True}


class PRStatus(enum.Enum):
    OPEN = 'OPEN'
    MERGED = 'MERGED'


class Team(Base):
    __tablename__ = 'teams'

    team_name: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        unique=True,
        index=True
    )

    members: Mapped[List['User']] = relationship(
        'User',
        back_populates='team',
        cascade='all, delete-orphan',
        lazy='selectin'
    )


class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    team_name: Mapped[str] = mapped_column(
        String,
        ForeignKey('teams.team_name'),
        nullable=False
    )

    team: Mapped['Team'] = relationship(
        'Team',
        back_populates='members',
        lazy='selectin'
    )

    authored_pull_requests: Mapped[List['PullRequest']] = relationship(
        'PullRequest',
        back_populates='author',
        foreign_keys='PullRequest.author_id',
        lazy='selectin'
    )

    reviewer_associations: Mapped[List['PullRequestReviewer']] = relationship(
        'PullRequestReviewer',
        back_populates='user',
        lazy='selectin',
        cascade='all, delete-orphan'
    )

    assigned_reviews: Mapped[List['PullRequest']] = association_proxy(
        'reviewer_associations', 'pull_request'
    )


class PullRequest(Base):
    __tablename__ = 'pull_requests'

    pull_request_id: Mapped[str] = mapped_column(String, primary_key=True)
    pull_request_name: Mapped[str] = mapped_column(String, nullable=False)

    status: Mapped[PRStatus] = mapped_column(
        Enum(PRStatus, name='pr_status_enum'),
        nullable=False,
        default=PRStatus.OPEN
    )

    author_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('users.user_id'),
        nullable=False
    )

    author: Mapped['User'] = relationship(
        'User',
        back_populates='authored_pull_requests',
        foreign_keys=[author_id],
        lazy='selectin'
    )

    reviewer_associations: Mapped[List['PullRequestReviewer']] = relationship(
        'PullRequestReviewer',
        back_populates='pull_request',
        lazy='selectin',
        cascade='all, delete-orphan'
    )

    assigned_reviewers: Mapped[List['User']] = association_proxy(
        'reviewer_associations', 'user'
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    merged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )


class PullRequestReviewer(Base):
    __tablename__ = 'pull_request_reviewers'

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('users.user_id'),
        primary_key=True
    )
    pull_request_id: Mapped[str] = mapped_column(
        String,
        ForeignKey('pull_requests.pull_request_id'),
        primary_key=True
    )

    user: Mapped['User'] = relationship(
        'User',
        back_populates='reviewer_associations',
        lazy='selectin'
    )
    pull_request: Mapped['PullRequest'] = relationship(
        'PullRequest',
        back_populates='reviewer_associations',
        lazy='selectin'
    )
