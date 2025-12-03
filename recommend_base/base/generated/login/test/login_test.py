import pytest
import requests

BASE_URL = "http://localhost:8000"


def test_login_case_TC_LOGIN_001():
    """정상 로그인"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "email": "user1@example.com",
        "password": "Pass@word1"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 200, f"Expected status 200 but got {response.status_code}"
    json_data = response.json()
    for key in ("accessToken", "userId"):
        assert key in json_data, f"Response JSON missing key '{key}'"


def test_login_case_TC_LOGIN_002():
    """잘못된 비밀번호"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "email": "user1@example.com",
        "password": "WrongPass!1"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 401, f"Expected status 401 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON missing 'errorCode'"
    assert json_data["errorCode"] == "LOGIN_FAILED", f"Expected errorCode 'LOGIN_FAILED' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_003():
    """비밀번호 형식 오류"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "email": "user1@example.com",
        "password": "short"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 400, f"Expected status 400 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON missing 'errorCode'"
    assert json_data["errorCode"] == "INVALID_PASSWORD_FORMAT", f"Expected errorCode 'INVALID_PASSWORD_FORMAT' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_004():
    """5회 연속 로그인 실패 후 계정 잠김"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "email": "user1@example.com",
        "password": "WrongPass!1"
    }
    # 1~4번째 로그인 실패 (LOGIN_FAILED 유지)
    for i in range(4):
        response = requests.post(url, json=payload)
        assert response.status_code == 401, f"Attempt {i+1}: Expected status 401 but got {response.status_code}"
        json_data = response.json()
        assert "errorCode" in json_data, f"Attempt {i+1}: Response JSON missing 'errorCode'"
        assert json_data["errorCode"] == "LOGIN_FAILED", f"Attempt {i+1}: Expected errorCode 'LOGIN_FAILED' but got '{json_data['errorCode']}'"
    # 5번째 로그인 실패 시 계정 잠김 발생
    response = requests.post(url, json=payload)
    assert response.status_code == 401, f"Attempt 5: Expected status 401 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Attempt 5: Response JSON missing 'errorCode'"
    assert json_data["errorCode"] == "ACCOUNT_LOCKED", f"Attempt 5: Expected errorCode 'ACCOUNT_LOCKED' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_005():
    """잠긴 계정으로 로그인 시도"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "email": "user1@example.com",
        "password": "Pass@word1"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 401, f"Expected status 401 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON missing 'errorCode'"
    assert json_data["errorCode"] == "ACCOUNT_LOCKED", f"Expected errorCode 'ACCOUNT_LOCKED' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_006():
    """이메일 형식 오류"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "email": "invalid-email-format",
        "password": "Pass@word1"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 400, f"Expected status 400 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON missing 'errorCode'"
    assert json_data["errorCode"] == "INVALID_EMAIL_FORMAT", f"Expected errorCode 'INVALID_EMAIL_FORMAT' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_007():
    """이메일 누락"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "password": "Pass@word1"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 400, f"Expected status 400 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON missing 'errorCode'"
    assert json_data["errorCode"] == "MISSING_REQUIRED_FIELD", f"Expected errorCode 'MISSING_REQUIRED_FIELD' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_008():
    """비밀번호 누락"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "email": "user1@example.com"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 400, f"Expected status 400 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON missing 'errorCode'"
    assert json_data["errorCode"] == "MISSING_REQUIRED_FIELD", f"Expected errorCode 'MISSING_REQUIRED_FIELD' but got '{json_data['errorCode']}'"


def test_login_case_TC_LOGIN_009():
    """존재하지 않는 이메일로 로그인 시도"""
    url = f"{BASE_URL}/api/login_api"
    payload = {
        "email": "notfound@example.com",
        "password": "Pass@word1"
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 401, f"Expected status 401 but got {response.status_code}"
    json_data = response.json()
    assert "errorCode" in json_data, "Response JSON missing 'errorCode'"
    assert json_data["errorCode"] == "LOGIN_FAILED", f"Expected errorCode 'LOGIN_FAILED' but got '{json_data['errorCode']}'"