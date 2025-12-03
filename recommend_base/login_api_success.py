# login_api_success.py
"""
테스트용: login_api_fail.py에서 지적될 만한 문제를 개선한 로그인 API 예제
- 입력 검증 강화 (Pydantic 모델, EmailStr, 길이 제한)
- 비밀번호 해시 저장/검증 (passlib 사용)
- SQL Injection 방지 (파라미터 바인딩)
- 민감정보를 로그/응답에 노출하지 않음
- 환경 변수 기반 설정 구조
- 예외 처리 및 에러 메시지 개선
- 사용하지 않는 import 제거, logging 모듈 사용
"""

import os
import logging
from pathlib import Path
from typing import Optional

import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from passlib.context import CryptContext

# -----------------------------
# 설정 및 로거 구성
# -----------------------------
DB_PATH = os.getenv("APP_DB_PATH", "users_secure.db")
APP_ENV = os.getenv("APP_ENV", "local")  # local / dev / prod 등
LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("login_api")

# 비밀번호 해시 컨텍스트 (bcrypt 사용)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# Pydantic 모델
# -----------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        if len(v) > 128:
            raise ValueError("비밀번호는 최대 128자를 초과할 수 없습니다.")
        return v


class LoginResponse(BaseModel):
    user_id: int
    email: EmailStr
    role: str


# -----------------------------
# 초기 DB 스키마 및 테스트 데이터
# -----------------------------
def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'USER'
        )
        """
    )
    conn.commit()

    # 테스트용 계정 1개 삽입 (이미 있으면 무시)
    test_email = "user1@example.com"
    test_password = "Password!1"
    password_hash = pwd_context.hash(test_password)

    cur.execute("SELECT id FROM users WHERE email = ?", (test_email,))
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
            (test_email, password_hash, "USER"),
        )
        conn.commit()
        logger.info("테스트 사용자 생성: %s", test_email)
    conn.close()


app = FastAPI(on_startup=[init_db])


# -----------------------------
# 로그인 API
# -----------------------------
@app.post("/api/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """
    안전한 로그인 처리 예제:
    - 입력은 Pydantic으로 검증
    - SQL은 파라미터 바인딩 사용
    - 비밀번호는 bcrypt 해시로 비교
    - 응답/로그에 비밀번호 등 민감정보 노출 금지
    """

    logger.info("로그인 시도: email=%s", req.email)

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # SQL Injection 방지: 파라미터 바인딩 사용
        cur.execute(
            "SELECT id, email, password_hash, role FROM users WHERE email = ?",
            (req.email,),
        )
        row = cur.fetchone()
    except Exception as e:
        logger.exception("로그인 처리 중 DB 오류 발생")  # 내부에만 상세 로그
        raise HTTPException(
            status_code=500,
            detail="일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        )
    finally:
        conn.close()

    if not row:
        # ID가 존재하지 않는 경우
        logger.warning("로그인 실패 - 존재하지 않는 이메일: %s", req.email)
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    stored_hash = row["password_hash"]
    if not pwd_context.verify(req.password, stored_hash):
        logger.warning("로그인 실패 - 비밀번호 불일치: %s", req.email)
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    # 여기까지 왔다면 성공
    logger.info("로그인 성공: user_id=%s, email=%s", row["id"], row["email"])

    return LoginResponse(
        user_id=row["id"],
        email=row["email"],
        role=row["role"],
    )


# -----------------------------
# 전역 예외 처리 예시 (선택)
# -----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.exception("처리되지 않은 예외 발생: %s %s", request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "시스템 오류가 발생했습니다. 관리자에게 문의해 주세요."},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("login_api_success:app", host="0.0.0.0", port=8001, reload=True)
