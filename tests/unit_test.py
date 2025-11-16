import pytest
from database.models import PRStatus
from database.crud.user_crud import UserCrud


class MockPR:
    def __init__(self, status):
        self.status = status


class MockUser:
    def __init__(self, user_id, open_reviews_count):
        self.user_id = user_id
        self.assigned_reviews = [
            MockPR(PRStatus.OPEN) for _ in range(open_reviews_count)
        ]
        self.assigned_reviews.append(MockPR(PRStatus.MERGED))


@pytest.mark.asyncio
async def test_select_reviewers_weighted():
    user_newbie = MockUser(user_id="newbie", open_reviews_count=0)
    user_vet = MockUser(user_id="vet", open_reviews_count=5)

    candidates = [user_newbie, user_vet]

    selections = {
        "newbie": 0,
        "vet": 0
    }

    for _ in range(100):
        selected_list = await UserCrud.select_reviewers_weighted(candidates)
        assert len(selected_list) == 2

        assert await UserCrud.select_reviewers_weighted([]) == []

        assert await UserCrud.select_reviewers_weighted([user_newbie]) == [user_newbie]

        selected_2 = await UserCrud.select_reviewers_weighted([user_newbie, user_vet])
        assert len(selected_2) == 2
        assert user_newbie in selected_2
        assert user_vet in selected_2

        user_newbie_2 = MockUser(user_id="newbie2", open_reviews_count=1)
        candidates_real = [user_newbie, user_newbie_2, user_vet]

        for _ in range(100):
            selected = await UserCrud.select_reviewers_weighted(candidates_real)
            assert len(selected) == 2
            for user in selected:
                selections[user.user_id] = selections.get(user.user_id, 0) + 1

    print(f"Selections: {selections}")
    assert selections.get("vet", 0) < selections.get("newbie", 0)
    assert selections.get("vet", 0) < selections.get("newbie2", 0)
