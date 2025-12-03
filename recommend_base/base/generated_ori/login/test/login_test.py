import requests

BASE_URL = "http://localhost:8000"


def test_login_case_TC_LOGIN_001():
    """
    TC_LOGIN_001: 정상 로그인
    Precondition: 사용자 user1@example.com, 비밀번호 Pass@word1 가 사전에 등록되어 있음
    """
    payload = {
        "email": "user1@example.com",
        "password": "Pass@word1"
    }
    response = requests.post(f"{BASE_URL}/api/login_api", json=payload)
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    json_data = response.json()
    assert "accessToken" in json_data, "Response JSON does not contain 'accessToken'"
    assert "userId" in json_data, "Response JSON does not contain 'userId'"


def test_login_case_TC_LOGIN_002():
    """
    TC_LOGIN_002: 이메일 형식 오류
    """
    payload = {
        "email": "user1example.com",
        "password": "Pass@word1"
    }
    response = requests.post(f"{BASE_URL}/api/login_api", json=payload)
    assert response.status_code == 400, f"Expected status code 400 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON does not contain 'errorCode'"
    assert json_data["errorCode"] == "INVALID_EMAIL_FORMAT", f"Expected errorCode 'INVALID_EMAIL_FORMAT' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_003():
    """
    TC_LOGIN_003: 비밀번호 길이 부족
    """
    payload = {
        "email": "user1@example.com",
        "password": "Abc1!"
    }
    response = requests.post(f"{BASE_URL}/api/login_api", json=payload)
    assert response.status_code == 400, f"Expected status code 400 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON does not contain 'errorCode'"
    assert json_data["errorCode"] == "INVALID_PASSWORD_FORMAT", f"Expected errorCode 'INVALID_PASSWORD_FORMAT' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_004():
    """
    TC_LOGIN_004: 비밀번호 복잡성 미충족(특수문자 없음)
    """
    payload = {
        "email": "user1@example.com",
        "password": "Abcd1234"
    }
    response = requests.post(f"{BASE_URL}/api/login_api", json=payload)
    assert response.status_code == 400, f"Expected status code 400 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON does not contain 'errorCode'"
    assert json_data["errorCode"] == "INVALID_PASSWORD_FORMAT", f"Expected errorCode 'INVALID_PASSWORD_FORMAT' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_005():
    """
    TC_LOGIN_005: 존재하지 않는 사용자
    """
    payload = {
        "email": "unknown@example.com",
        "password": "Pass@word1"
    }
    response = requests.post(f"{BASE_URL}/api/login_api", json=payload)
    assert response.status_code == 401, f"Expected status code 401 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON does not contain 'errorCode'"
    assert json_data["errorCode"] == "LOGIN_FAILED", f"Expected errorCode 'LOGIN_FAILED' but got '{json_data['errorCode']}'"