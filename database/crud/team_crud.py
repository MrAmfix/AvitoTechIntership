from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Team


class TeamCrud:
    @staticmethod
    async def get_by_name(session: AsyncSession, team_name: str) -> Optional[Team]:
        team = await session.get(Team, team_name)
        return team

    @staticmethod
    async def create(session: AsyncSession, team_name: str):
        team = Team(team_name=team_name)
        session.add(team)

        return team
