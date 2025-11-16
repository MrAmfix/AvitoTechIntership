from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import PullRequestCreateSchema
from database.models import PullRequest, User


class PullRequestCrud:
    @staticmethod
    async def get_by_id(session: AsyncSession, pull_request_id: str) -> Optional[PullRequest]:
        pr = await session.get(PullRequest, pull_request_id)
        return pr

    @staticmethod
    async def create(
            session: AsyncSession,
            pr_data: PullRequestCreateSchema,
            author: User,
            reviewers: List[User]
    ) -> PullRequest:
        new_pr = PullRequest(
            pull_request_id=pr_data.pull_request_id,
            pull_request_name=pr_data.pull_request_name,
            author_id=author.user_id,
            assigned_reviewers=reviewers
        )
        session.add(new_pr)
        return new_pr
