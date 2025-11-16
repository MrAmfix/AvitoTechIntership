from random import choices
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, PRStatus


class UserCrud:
    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
        user = await session.get(User, user_id)
        return user

    @staticmethod
    async def create_or_update(
            session: AsyncSession,
            user_id: str,
            username: str,
            is_active: bool,
            team_name: str
    ) -> User:
        user = await UserCrud.get_by_id(session, user_id)

        if user:
            user.username = username
            user.is_active = is_active
            user.team_name = team_name
        else:
            user = User(
                user_id=user_id,
                username=username,
                is_active=is_active,
                team_name=team_name
            )
            session.add(user)

        return user

    @staticmethod
    async def get_active_candidates(
            session: AsyncSession,
            team_name: str,
            exclude_ids: List[str]
    ) -> List[User]:
        result = await session.execute(
            select(User)
            .where(
                User.team_name == team_name,
                User.is_active.is_(True),
                User.user_id.notin_(exclude_ids)
            )
        )

        return result.scalars().all()

    @staticmethod
    async def select_reviewers_weighted(
            candidates: List[User]
    ) -> List[User]:
        if not candidates:
            return []
        if len(candidates) <= 2:
            return candidates


        candidate_weights = []
        for user in candidates:
            open_reviews_count = sum(
                1 for pr in user.assigned_reviews
                if pr.status == PRStatus.OPEN
            )

            weight = 1 / (1 + open_reviews_count)
            candidate_weights.append((user, weight))

        users_pool = [cw[0] for cw in candidate_weights]
        weights_pool = [cw[1] for cw in candidate_weights]

        selected_reviewers = []

        reviewer1 = choices(users_pool, weights=weights_pool, k=1)[0]
        selected_reviewers.append(reviewer1)

        idx_to_remove = users_pool.index(reviewer1)

        users_pool.pop(idx_to_remove)
        weights_pool.pop(idx_to_remove)

        reviewer2 = choices(users_pool, weights=weights_pool, k=1)[0]
        selected_reviewers.append(reviewer2)

        return selected_reviewers
