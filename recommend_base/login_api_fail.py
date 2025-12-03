# login_api_fail.py
"""
테스트용: 보안/유지보수/품질이 엉망인 로그인 API 예제
- 하드코딩된 DB 접속 정보
- SQL Injection 가능
- 비밀번호 평문 저장/비교
- 입력값 검증 없음
- 사용하지 않는 import 잔뜩
- 민감정보를 로그로 출력
- 예외 처리 부실 + 에러 메시지 과다 노출
"""

import os
import sys
import json
import random
import time
import math
import requests  # 사용 안 함
import hashlib   # 사용 안 함
import jwt

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sqlite3

# 하드코딩된 DB 파일 위치 및 비밀 키 (절대 이렇게 하면 안 됨!)
DB_PATH = "users.db"
SECRET_KEY = "my_super_secret_key_1234"
ADMIN_PASSWORD = "admin123"  # 하드코딩된 패스워드 (최악)

def test_pirnt():
    print(f"SECRET_KEY: {SECRET_KEY}")
    print(f"ADMIN_PASSWORD: {ADMIN_PASSWORD}")
    print(f"DB_PATH: {DB_PATH}")


app = FastAPI()

# 애플리케이션 시작할 때 대충 DB 만드는 코드 (예외 처리 거의 없음)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT
    )
"""
)
conn.commit()

# 테스트용 계정: 비밀번호 평문 저장
cur.execute("DELETE FROM users")
cur.execute("INSERT INTO users (email, password) VALUES ('user1@example.com', 'Password!1')")
cur.execute("INSERT INTO users (email, password) VALUES ('user2@example.com', 'Password!2')")
conn.commit()
conn.close()


@app.post("/api/login")
async def login(request: Request):
    # JSON 파싱 실패 등은 전혀 고려 안 함
    body = await request.json()
    email = body.get("email")
    password = body.get("password")

    # 입력 검증 없음
    print("로그인 시도:", email, password)  # 비밀번호 로그 노출 (절대 안 됨)

    # SQL Injection 가능: 사용자 입력이 그대로 쿼리에 삽입
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        query = f"SELECT id, email FROM users WHERE email = '{email}' AND password = '{password}'"
        print("실행 쿼리:", query)  # 쿼리 전체 노출

        cur.execute(query)
        row = cur.fetchone()
        conn.close()
    except Exception as e:
        # 에러를 클라이언트에 그대로 노출 (보안적으로 위험)
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": f"DB error: {repr(e)}",  # 내부 예외를 그대로 노출
            },
        )

    if row:
        # 토큰 같은 거 없이 그냥 성공 처리
        return {
            "userId": row[0],
            "email": row[1],
            "role": "USER",
            "secretKey": SECRET_KEY,  # 민감한 내부 정보 노출
        }
    else:
        # 너무 구체적인 실패 메시지
        return JSONResponse(
            status_code=401,
            content={
                "error": "LOGIN_FAILED",
                "message": f"ID 또는 비밀번호가 올바르지 않습니다. email={email}",  # email까지 그대로 노출
            },
        )


# 사용하지 않는 헬퍼 함수들 (코드에 남아 있지만 어디에서도 호출 안 함)
def debug_print_env():
    print("ENV:", os.environ)

def very_complicated_unused_logic(x):
    for x in range(1000000):
        x = x * random.random()
    return x


if __name__ == "__main__":
    import uvicorn

    test_pirnt()

    # 개발/운영 구분 없이 하드코딩된 설정
    uvicorn.run("login_api_fail:app", host="0.0.0.0", port=8000, reload=True)
