from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_200_OK, \
    HTTP_404_NOT_FOUND

from api.schemas import TeamResponseSchema, TeamCreateSchema
from database.crud.team_crud import TeamCrud
from database.crud.user_crud import UserCrud
from database.gen_session import get_session


t_router = APIRouter(prefix='/team')


@t_router.post(
    '/add',
    response_model=TeamResponseSchema,
    status_code=HTTP_201_CREATED
)
async def team_add(
        team_data: TeamCreateSchema,
        session: AsyncSession = Depends(get_session)
):
    try:
        team = await TeamCrud.get_by_name(session, team_data.team_name)

        if team:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "TEAM_EXISTS", "message": "team_name already exists"}}
            )

        new_team = await TeamCrud.create(session, team_data.team_name)
        for user in team_data.members:
            await UserCrud.create_or_update(
                session,
                user_id=user.user_id,
                username=user.username,
                is_active=user.is_active,
                team_name=new_team.team_name
            )

        await session.commit()
        await session.refresh(new_team)

        return new_team

    except HTTPException as _he:
        await session.rollback()
        raise _he
    except Exception as _e:
        await session.rollback()
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": f"Unexpected error: {_e}"}}
        )


@t_router.get(
    '/get',
    response_model=TeamResponseSchema,
    status_code=HTTP_200_OK
)
async def team_get(
    team_name: str = Query(...),
    session: AsyncSession = Depends(get_session)
):
    team = await TeamCrud.get_by_name(session, team_name)

    if not team:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Team not found"}
        )

    return team
