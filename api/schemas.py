from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field, Field
from typing import List, Optional

from database.models import PRStatus


# === Для team.py ===


class TeamMemberCreateSchema(BaseModel):
    user_id: str
    username: str
    is_active: bool


class TeamCreateSchema(BaseModel):
    team_name: str
    members: List[TeamMemberCreateSchema]


class TeamMemberResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    is_active: bool


class TeamResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_name: str
    members: List[TeamMemberResponseSchema]


# === Для users.py ===


class UserSetIsActiveSchema(BaseModel):
    user_id: str
    is_active: bool


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    team_name: str
    is_active: bool


class PullRequestShortSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pull_request_id: str
    pull_request_name: str
    author_id: str
    status: PRStatus


class UserReviewListSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    pull_requests: List[PullRequestShortSchema]


# === Для pull_request.py ===


class PullRequestCreateSchema(BaseModel):
    pull_request_id: str
    pull_request_name: str
    author_id: str


class PullRequestResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pull_request_id: str
    pull_request_name: str
    author_id: str
    status: PRStatus
    created_at: datetime
    merged_at: Optional[datetime] = None

    assigned_reviewers_rels: List[UserResponseSchema] = Field(
        validation_alias="assigned_reviewers"
    )

    @computed_field
    @property
    def assigned_reviewers(self) -> List[str]:
        return [user.user_id for user in self.assigned_reviewers_rels]


class PullRequestMergeSchema(BaseModel):
    pull_request_id: str


class PullRequestReassignSchema(BaseModel):
    pull_request_id: str
    old_user_id: str


class PullRequestReassignResponseSchema(BaseModel):
    pr: PullRequestResponseSchema
    replaced_by: str
