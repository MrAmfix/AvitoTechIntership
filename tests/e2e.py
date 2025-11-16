import requests
import json
import time

BASE_URL = "http://localhost:8080"

run_id = int(time.time() * 1000)
TEAM_NAME = f"team_{run_id}"
PR_ID = f"pr_{run_id}"

USER_AUTHOR = f"u_author_{run_id}"
USER_REV_A = f"u_rev_a_{run_id}"
USER_REV_B = f"u_rev_b_{run_id}"
USER_REV_C_REPLACEMENT = f"u_rev_c_repl_{run_id}"


def print_step(title):
    print("\n" + "=" * 80)
    print(f"--- {title.upper()} ---")
    print("=" * 80)


def print_request(method, url, payload=None):
    print(f"REQUEST: {method} {url}")
    if payload:
        print(f"PAYLOAD: {json.dumps(payload, indent=2, ensure_ascii=False)}")


def print_response(response):
    print(f"RESPONSE: {response.status_code}")
    try:
        print(f"DATA: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except requests.exceptions.JSONDecodeError:
        print(f"DATA: (No JSON body)")
    print("-" * 80)


def run_test_flow():
    """
    Выполняет полный E2E-тест API
    """
    try:
        print_step("1. СОЗДАНИЕ КОМАНДЫ")
        team_payload = {
            "team_name": TEAM_NAME,
            "members": [
                {"user_id": USER_AUTHOR, "username": "Автор Alice", "is_active": True},
                {"user_id": USER_REV_A, "username": "Ревьюер Bob", "is_active": True},
                {"user_id": USER_REV_B, "username": "Ревьюер Charlie", "is_active": True},
                {"user_id": USER_REV_C_REPLACEMENT, "username": "Замена David", "is_active": True}
            ]
        }
        print_request("POST", f"{BASE_URL}/team/add", team_payload)
        resp = requests.post(f"{BASE_URL}/team/add", json=team_payload)
        print_response(resp)
        assert resp.status_code == 201

        print_step("2. ПОЛУЧЕНИЕ КОМАНДЫ (/team/get)")
        print_request("GET", f"{BASE_URL}/team/get?team_name={TEAM_NAME}")
        resp = requests.get(f"{BASE_URL}/team/get", params={"team_name": TEAM_NAME})
        print_response(resp)
        assert resp.status_code == 200
        assert len(resp.json()['members']) == 4

        print_step("3. СОЗДАНИЕ PR (ТЕСТ АВТОНАЗНАЧЕНИЯ)")
        pr_payload = {
            "pull_request_id": PR_ID,
            "pull_request_name": "Новая фича",
            "author_id": USER_AUTHOR
        }
        print_request("POST", f"{BASE_URL}/pullRequest/create", pr_payload)
        resp = requests.post(f"{BASE_URL}/pullRequest/create", json=pr_payload)
        print_response(resp)
        assert resp.status_code == 201
        pr_data = resp.json()
        assert len(pr_data['assigned_reviewers']) == 2, "Ожидалось 2 ревьюера"
        assert USER_AUTHOR not in pr_data['assigned_reviewers'], "Автор не должен быть ревьюером"

        original_reviewer_A = pr_data['assigned_reviewers'][0]
        original_reviewer_B = pr_data['assigned_reviewers'][1]

        print_step("4. ПОЛУЧЕНИЕ PR ДЛЯ РЕВЬЮ (/users/getReview)")
        print_request("GET", f"{BASE_URL}/users/getReview?user_id={original_reviewer_A}")
        resp = requests.get(f"{BASE_URL}/users/getReview", params={"user_id": original_reviewer_A})
        print_response(resp)
        assert resp.status_code == 200
        assert len(resp.json()['pull_requests']) == 1
        assert resp.json()['pull_requests'][0]['pull_request_id'] == PR_ID

        print_step("5. ПЕРЕНАЗНАЧЕНИЕ РЕВЬЮЕРА (/pullRequest/reassign)")

        all_possible_reviewers = {USER_REV_A, USER_REV_B, USER_REV_C_REPLACEMENT}
        initial_reviewers = {original_reviewer_A, original_reviewer_B}

        expected_replacement_set = all_possible_reviewers - initial_reviewers
        assert len(expected_replacement_set) == 1, "Логика теста нарушена, должен быть 1 кандидат"
        expected_replacement_id = expected_replacement_set.pop()

        print(f"INFO: Текущие ревьюеры: {initial_reviewers}")
        print(f"INFO: Ожидаемая замена (единственный, кто остался): {expected_replacement_id}")

        reassign_payload = {
            "pull_request_id": PR_ID,
            "old_user_id": original_reviewer_A
        }
        print_request("POST", f"{BASE_URL}/pullRequest/reassign", reassign_payload)
        resp = requests.post(f"{BASE_URL}/pullRequest/reassign", json=reassign_payload)
        print_response(resp)
        assert resp.status_code == 200

        reassign_data = resp.json()
        new_reviewer = reassign_data['replaced_by']

        assert new_reviewer == expected_replacement_id, f"Ожидалась замена на {expected_replacement_id}, но получили {new_reviewer}"

        current_reviewers = reassign_data['pr']['assigned_reviewers']
        assert original_reviewer_A not in current_reviewers
        assert original_reviewer_B in current_reviewers
        assert new_reviewer in current_reviewers

        print_step("6. ДЕАКТИВАЦИЯ РЕВЬЮЕРА (/users/setIsActive)")
        deact_payload = {
            "user_id": original_reviewer_B,
            "is_active": False
        }
        print_request("POST", f"{BASE_URL}/users/setIsActive", deact_payload)
        resp = requests.post(f"{BASE_URL}/users/setIsActive", json=deact_payload)
        print_response(resp)
        assert resp.status_code == 200
        assert resp.json()['is_active'] == False

        print_step("7. СЛИЯНИЕ PR (/pullRequest/merge)")
        merge_payload = {"pull_request_id": PR_ID}
        print_request("POST", f"{BASE_URL}/pullRequest/merge", merge_payload)
        resp = requests.post(f"{BASE_URL}/pullRequest/merge", json=merge_payload)
        print_response(resp)
        assert resp.status_code == 200
        merged_pr_data = resp.json()
        assert merged_pr_data['status'] == "MERGED"

        print("\n--- ПРОВЕРКА ЛОГИКИ ДЕАКТИВАЦИИ ---")

        assert original_reviewer_B not in merged_pr_data['assigned_reviewers']

        assert original_reviewer_A in merged_pr_data['assigned_reviewers']

        assert new_reviewer in merged_pr_data['assigned_reviewers']

        assert len(merged_pr_data['assigned_reviewers']) == 2

        print_step("8. ТЕСТ ИДЕМПОТЕНТНОСТИ (ПОВТОРНЫЙ MERGE)")
        print_request("POST", f"{BASE_URL}/pullRequest/merge", merge_payload)
        resp = requests.post(f"{BASE_URL}/pullRequest/merge", json=merge_payload)
        print_response(resp)
        assert resp.status_code == 200, "Идемпотентный merge должен возвращать 200"

        print_step("9. ТЕСТ ОШИБКИ (REASSIGN ПОСЛЕ MERGE)")
        reassign_payload_fail = {
            "pull_request_id": PR_ID,
            "old_user_id": new_reviewer
        }
        print_request("POST", f"{BASE_URL}/pullRequest/reassign", reassign_payload_fail)
        resp = requests.post(f"{BASE_URL}/pullRequest/reassign", json=reassign_payload_fail)
        print_response(resp)
        assert resp.status_code == 409
        assert resp.json()['detail']['error']['code'] == "PR_MERGED"

        print_step("10. ТЕСТ ОШИБКИ (404 NOT FOUND)")
        print_request("GET", f"{BASE_URL}/team/get?team_name=non-existent-team")
        resp = requests.get(f"{BASE_URL}/team/get", params={"team_name": "non-existent-team"})
        print_response(resp)
        assert resp.status_code == 404

        assert resp.json()['detail']['code'] == "NOT_FOUND"

        print_step("ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")

        print_step("ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")

    except AssertionError as e:
        print("\n" + "!" * 80)
        print(f"!!! ТЕСТ ПРОВАЛЕН !!!")
        print(f"ОШИБКА: {e}")
        print("!" * 80)
    except requests.exceptions.ConnectionError:
        print("\n" + "!" * 80)
        print("!!! ТЕСТ ПРОВАЛЕН !!!")
        print(f"НЕ УДАЛОСЬ ПОДКЛЮЧИТЬСЯ К {BASE_URL}")
        print("Убедись, что 'docker-compose up' запущен.")
        print("!" * 80)


if __name__ == "__main__":
    run_test_flow()
