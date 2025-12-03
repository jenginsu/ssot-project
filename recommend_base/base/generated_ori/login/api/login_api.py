from datetime import datetime, timedelta
import re
from typing import Any

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import String, DateTime, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import bcrypt
import jwt

# Configuration constants
DATABASE_URL = "mysql+asyncmy://user:password@localhost/ssot"
JWT_SECRET_KEY = "your-secure-secret-key"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(title="Login API", version="1.0.0")

# SQLAlchemy Declarative Base
class Base(DeclarativeBase):
    pass

# Member ORM model
class Member(Base):
    __tablename__ = "tbl_member"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

# Async DB engine and sessionmaker
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Pydantic model for request body
class LoginInput(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    def password_length_and_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("INVALID_PASSWORD_FORMAT")
        # Must contain at least one uppercase, one lowercase, one digit, one special char
        pattern = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*])")
        if not pattern.search(v):
            raise ValueError("INVALID_PASSWORD_FORMAT")
        return v

# Pydantic model for success response
class LoginSuccessResponse(BaseModel):
    accessToken: str
    userId: str

# Pydantic model for error response
class ErrorResponse(BaseModel):
    errorCode: str

# Dependency to get async DB session
async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Utility function to verify password using bcrypt
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

# Utility function to create JWT access token
def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

# Custom exception handler for validation errors to map to errorCode
@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    msg = str(exc)
    if msg == "INVALID_PASSWORD_FORMAT":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"errorCode": "INVALID_PASSWORD_FORMAT"},
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"errorCode": "MISSING_REQUIRED_FIELD"},
    )

# POST /api/login_api endpoint
@app.post("/api/login_api", response_model=LoginSuccessResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
})
async def login_api(input_data: LoginInput, session: AsyncSession = Depends(get_db_session)) -> Any:
    # Email format is validated by EmailStr, if invalid FastAPI returns 422 automatically.
    # But per spec, we must return 400 with INVALID_EMAIL_FORMAT if email format invalid.
    # So we do manual check here:
    email = input_data.email
    password = input_data.password

    # Additional email format validation per RFC-5322 (already covered by EmailStr)
    # But to strictly follow SSOT, catch validation errors and return 400 with INVALID_EMAIL_FORMAT
    # This is handled by FastAPI validation, so we catch RequestValidationError globally below.

    # Query user by email
    stmt = select(Member).where(Member.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # User not found
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"errorCode": "LOGIN_FAILED"},
        )

    # Verify password
    if not verify_password(password, user.password_hash):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"errorCode": "LOGIN_FAILED"},
        )

    # Create access token
    access_token = create_access_token(user.user_id)

    return LoginSuccessResponse(accessToken=access_token, userId=user.user_id)

# Override default validation error handler to map email format errors to INVALID_EMAIL_FORMAT
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi import Depends

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Inspect errors to find if email format error exists
    for err in exc.errors():
        loc = err.get("loc", [])
        msg = err.get("msg", "")
        typ = err.get("type", "")
        if loc and loc[-1] == "email":
            # Email field error
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"errorCode": "INVALID_EMAIL_FORMAT"},
            )
        if loc and loc[-1] == "password":
            # Password field error
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"errorCode": "INVALID_PASSWORD_FORMAT"},
            )
        if typ == "value_error.missing":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"errorCode": "MISSING_REQUIRED_FIELD"},
            )
    # Default fallback
    return await request_validation_exception_handler(request, exc)