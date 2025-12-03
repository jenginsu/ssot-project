from datetime import datetime
import re
from typing import Any

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import Boolean, Column, DateTime, Integer, String, select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import bcrypt
import jwt

# Constants from business rules
MAX_FAIL_COUNT = 5
FAIL_ERROR_CODE = "LOGIN_FAILED"
LOCK_ERROR_CODE = "ACCOUNT_LOCKED"
MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
INVALID_EMAIL_FORMAT = "INVALID_EMAIL_FORMAT"
INVALID_PASSWORD_FORMAT = "INVALID_PASSWORD_FORMAT"

JWT_SECRET_KEY = "your-secure-secret-key"  # In production, use env var or secret manager
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 3600  # 1 hour token expiry


app = FastAPI(
    title="로그인 기능 API",
    version="1.0.0",
    description="사용자 로그인 API",
)


class Base(DeclarativeBase):
    pass


class Member(Base):
    __tablename__ = "tbl_member"
    __table_args__ = {"schema": "ssot"}

    user_id = Column(String(20), primary_key=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    fail_count = Column(Integer, nullable=False, default=0)
    is_locked = Column(Boolean, nullable=False, default=False)
    locked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


DATABASE_URL = "mysql+asyncmy://user:password@localhost/ssot?charset=utf8mb4"
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v is None:
            raise ValueError(MISSING_REQUIRED_FIELD)
        if len(v) > 255:
            raise ValueError(INVALID_EMAIL_FORMAT)
        # Use EmailStr to validate format
        try:
            EmailStr.validate(v)
        except Exception:
            raise ValueError(INVALID_EMAIL_FORMAT)
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if v is None:
            raise ValueError(MISSING_REQUIRED_FIELD)
        if len(v) < 8:
            raise ValueError(INVALID_PASSWORD_FORMAT)
        pattern = re.compile(r"(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}")
        if not pattern.fullmatch(v):
            raise ValueError(INVALID_PASSWORD_FORMAT)
        return v

    model_config = dict(extra="forbid")


class LoginResponse(BaseModel):
    accessToken: str
    userId: str


class ErrorResponse(BaseModel):
    errorCode: str


def create_access_token(user_id: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now.timestamp() + JWT_EXPIRE_SECONDS,
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # Customize error response to match errorCode format
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        # exc.detail expected to be dict with errorCode
        if isinstance(exc.detail, dict) and "errorCode" in exc.detail:
            return JSONResponse(status_code=400, content=exc.detail)
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        if isinstance(exc.detail, dict) and "errorCode" in exc.detail:
            return JSONResponse(status_code=401, content=exc.detail)
    # fallback default
    return JSONResponse(status_code=exc.status_code, content={"errorCode": "UNKNOWN_ERROR"})


@app.post("/api/login_api", response_model=LoginResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
})
async def login_api(req: LoginRequest) -> Any:
    # Validate input is done by Pydantic automatically, but catch validation errors to return proper errorCode
    # We rely on Pydantic validation and field_validator raising ValueError with errorCode string

    # DB session
    async with AsyncSessionLocal() as session:
        # Lookup user by email
        stmt = select(Member).where(Member.email == req.email)
        result = await session.execute(stmt)
        member: Member | None = result.scalar_one_or_none()

        if member is None:
            # Email not found => LOGIN_FAILED
            raise HTTPException(status_code=401, detail={"errorCode": FAIL_ERROR_CODE})

        if member.is_locked:
            # Account locked
            raise HTTPException(status_code=401, detail={"errorCode": LOCK_ERROR_CODE})

        # Check password
        password_bytes = req.password.encode("utf-8")
        stored_hash_bytes = member.password_hash.encode("utf-8")
        if not bcrypt.checkpw(password_bytes, stored_hash_bytes):
            # Password mismatch
            member.fail_count += 1
            if member.fail_count >= MAX_FAIL_COUNT:
                member.is_locked = True
                member.locked_at = datetime.utcnow()
                await session.commit()
                raise HTTPException(status_code=401, detail={"errorCode": LOCK_ERROR_CODE})
            else:
                await session.commit()
                raise HTTPException(status_code=401, detail={"errorCode": FAIL_ERROR_CODE})

        # Password correct
        # Reset fail_count and unlock if locked (should not be locked here)
        if member.fail_count != 0 or member.is_locked:
            member.fail_count = 0
            member.is_locked = False
            member.locked_at = None
            member.updated_at = datetime.utcnow()
            await session.commit()

        # Create access token
        access_token = create_access_token(member.user_id)

        return LoginResponse(accessToken=access_token, userId=member.user_id)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    # This handles validation errors raised in field_validator with errorCode string
    error_code = str(exc)
    # Map known error codes to 400 or 401
    if error_code in {MISSING_REQUIRED_FIELD, INVALID_EMAIL_FORMAT, INVALID_PASSWORD_FORMAT}:
        return JSONResponse(status_code=400, content={"errorCode": error_code})
    # Unknown error code fallback
    return JSONResponse(status_code=400, content={"errorCode": "INVALID_REQUEST"})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # For unexpected errors, do not leak details
    return JSONResponse(status_code=500, content={"errorCode": "INTERNAL_SERVER_ERROR"})