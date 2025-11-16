from datetime import datetime
from random import choice

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND, \
    HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from api.schemas import PullRequestResponseSchema, PullRequestCreateSchema, PullRequestMergeSchema, \
    PullRequestReassignResponseSchema, PullRequestReassignSchema
from database.crud.pull_request_crud import PullRequestCrud
from database.crud.user_crud import UserCrud
from database.gen_session import get_session
from database.models import PRStatus

pr_router = APIRouter(prefix='/pullRequest')


@pr_router.post(
    '/create',
    response_model=PullRequestResponseSchema,
    status_code=HTTP_201_CREATED
)
async def pull_request_create(
    pr_data: PullRequestCreateSchema,
    session: AsyncSession = Depends(get_session)
):
    try:
        existing_pr = await PullRequestCrud.get_by_id(session, pr_data.pull_request_id)
        if existing_pr:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail={"error": {"code": "PR_EXISTS", "message": "PR id already exists"}}
            )

        author = await UserCrud.get_by_id(session, pr_data.author_id)
        if not author:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "Author not found"}}
            )
        if not author.is_active:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "AUTHOR_INACTIVE", "message": "Inactive user cannot create PR"}}
            )

        candidates = await UserCrud.get_active_candidates(
            session=session,
            team_name=author.team_name,
            exclude_ids=[author.user_id]
        )

        reviewers_to_assign = await UserCrud.select_reviewers_weighted(candidates)

        new_pr = await PullRequestCrud.create(
            session=session,
            pr_data=pr_data,
            author=author,
            reviewers=reviewers_to_assign
        )

        await session.commit()
        await session.refresh(new_pr)

        return new_pr

    except HTTPException as _he:
        await session.rollback()
        raise _he
    except Exception as _e:
        await session.rollback()
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": f"Unexpected error: {_e}"}}
        )


@pr_router.post(
    '/merge',
    response_model=PullRequestResponseSchema,
    status_code=HTTP_200_OK
)
async def pull_request_merge(
    pr_data: PullRequestMergeSchema,
    session: AsyncSession = Depends(get_session)
):
    try:
        pr = await PullRequestCrud.get_by_id(session, pr_data.pull_request_id)

        if not pr:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "PR not found"}}
            )

        if pr.status == PRStatus.OPEN:
            pr.status = PRStatus.MERGED
            pr.merged_at = datetime.now()

            await session.commit()
            await session.refresh(pr)

        return pr

    except HTTPException as _he:
        await session.rollback()
        raise _he
    except Exception as _e:
        await session.rollback()
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": f"Unexpected error: {_e}"}}
        )


@pr_router.post(
    '/reassign',
    response_model=PullRequestReassignResponseSchema,
    status_code=HTTP_200_OK
)
async def pull_request_reassign(
    reassign_data: PullRequestReassignSchema,
    session: AsyncSession = Depends(get_session)
):
    try:
        pr = await PullRequestCrud.get_by_id(session, reassign_data.pull_request_id)

        if not pr:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "PR not found"}}
            )

        if pr.status == PRStatus.MERGED:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail={"error": {"code": "PR_MERGED", "message": "cannot reassign on merged PR"}}
            )

        old_user = await UserCrud.get_by_id(session, reassign_data.old_user_id)
        if not old_user:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOT_FOUND", "message": "User to be replaced not found"}}
            )

        if old_user not in pr.assigned_reviewers:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail={"error": {"code": "NOT_ASSIGNED", "message": "Reviewer is not assigned to this PR"}}
            )

        exclude_ids = [pr.author_id]
        exclude_ids.extend([reviewer.user_id for reviewer in pr.assigned_reviewers])

        candidates = await UserCrud.get_active_candidates(
            session=session,
            team_name=old_user.team_name,
            exclude_ids=exclude_ids
        )

        if not candidates:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail={"error": {"code": "NO_CANDIDATE", "message": "No active replacement candidate in team"}}
            )

        new_reviewer = choice(candidates)

        pr.assigned_reviewers.remove(old_user)
        pr.assigned_reviewers.append(new_reviewer)

        await session.commit()
        await session.refresh(pr)

        return PullRequestReassignResponseSchema(
            pr=pr,
            replaced_by=new_reviewer.user_id
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
