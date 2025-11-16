from random import choice

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from api.schemas import UserResponseSchema, UserSetIsActiveSchema, UserReviewListSchema
from database.crud.user_crud import UserCrud
from database.gen_session import get_session
from database.models import PRStatus, PullRequestReviewer

u_router = APIRouter(prefix='/users')


@u_router.post(
    '/setIsActive',
    response_model=UserResponseSchema,
    status_code=HTTP_200_OK
)
async def user_set_is_active(
        user_data: UserSetIsActiveSchema,
        session: AsyncSession = Depends(get_session)
):
    try:
        user = await UserCrud.get_by_id(session, user_data.user_id)

        if not user:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "User not found"}}
            )

        if user.is_active == user_data.is_active:
            return user

        if user_data.is_active:
            user.is_active = True
            await session.commit()
            await session.refresh(user)
            return user

        open_prs_to_reassign = [
            assoc.pull_request for assoc in user.reviewer_associations
            if assoc.pull_request.status == PRStatus.OPEN
        ]

        user.is_active = False

        for pr in open_prs_to_reassign:
            exclude_ids = [pr.author_id]
            exclude_ids.extend([
                assoc.user_id for assoc in pr.reviewer_associations
                if assoc.user_id != user.user_id
            ])

            candidates = await UserCrud.get_active_candidates(
                session=session,
                team_name=user.team_name,
                exclude_ids=exclude_ids
            )

            if candidates:
                new_reviewer = choice(candidates)

                old_association = next(
                    (assoc for assoc in pr.reviewer_associations if assoc.user_id == user.user_id),
                    None
                )
                if old_association:
                    await session.delete(old_association)
                    await session.flush()

                new_association = PullRequestReviewer(
                    user_id=new_reviewer.user_id,
                    pull_request_id=pr.pull_request_id
                )
                session.add(new_association)
                await session.flush()

        await session.commit()
        await session.refresh(user)

        return user

    except HTTPException as _he:
        await session.rollback()
        raise _he
    except Exception as _e:
        await session.rollback()
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": f"Unexpected error: {_e}"}}
        )


@u_router.get(
    '/getReview',
    response_model=UserReviewListSchema,
    status_code=HTTP_200_OK
)
async def user_get_review(
    user_id: str = Query(...),
    session: AsyncSession = Depends(get_session)
):
    try:
        user = await UserCrud.get_by_id(session, user_id)

        if not user:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "User not found"}}
            )

        return UserReviewListSchema(
            user_id=user.user_id,
            pull_requests=user.assigned_reviews
        )

    except HTTPException as _he:
        await session.rollback()
        raise _he
    except Exception as _e:
        await session.rollback()
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": f"Unexpected error: {_e}"}}
        )
