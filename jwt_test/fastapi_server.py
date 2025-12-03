# fastapi_server.py
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field, constr, validator
import jwt
import re
import json
from typing import List

from config_auth import SECRET_KEY, ALGORITHM

# ---------------------------------------------------------
# FastAPI 앱 설정 (기본 응답을 ORJSONResponse로 설정 → 한글 깨짐 방지)
# ---------------------------------------------------------
app = FastAPI(default_response_class=ORJSONResponse)


# ---------------------------------------------------------
# 1. 입력 모델 정의 + 기본 입력 검증 (길이/포맷)
# ---------------------------------------------------------

# 허용 문자: 한글, 영문, 숫자, 공백, 기본 특수문자 정도만 허용
SAFE_QUESTION_REGEX = re.compile(
    r"^[ㄱ-ㅎ가-힣a-zA-Z0-9\s.,!?()\[\]\-_:+/\'\"@#&]+$"
)


class QuestionRequest(BaseModel):
    # Pydantic 레벨에서 최소/최대 길이 + 공백 제거
    question: constr(
        strip_whitespace=True,
        min_length=1,
        max_length=300,
    ) = Field(..., description="사용자 질문 (최대 300자)")

    @validator("question")
    def validate_question(cls, v: str) -> str:
        """
        1차 입력 검증:
        - 허용된 문자 세트만 허용
        - 필요 시 서비스 성격에 따라 regex 완화/강화 가능
        """
        if not SAFE_QUESTION_REGEX.match(v):
            raise ValueError(
                "질문에 허용되지 않은 문자가 포함되어 있습니다. "
                "한글/영문/숫자 및 일부 기본 특수문자만 사용할 수 있습니다."
            )
        return v


class CurrentUser(BaseModel):
    mbr_id: str


# ---------------------------------------------------------
# 2. JWT 기반 인증 / 인가 (SEC-001 대응)
# ---------------------------------------------------------
def get_current_user(authorization: str = Header(...)) -> CurrentUser:
    """
    Authorization: Bearer <JWT> 헤더를 파싱해서
    JWT를 검증하고 mbr_id(sub)를 꺼낸다.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    mbr_id = payload.get("sub")
    if not mbr_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return CurrentUser(mbr_id=mbr_id)


# ---------------------------------------------------------
# 3. 추가 입력 검증 및 Injection 방어 (SEC-002 대응)
# ---------------------------------------------------------

# 위험 패턴 예시 (서비스 상황에 따라 조정 가능)
DANGEROUS_PATTERNS: List[re.Pattern] = [
    # SQL 키워드들 (기본적인 것들만 예시로)
    re.compile(r"(?i)\b(select|insert|update|delete|drop|truncate|union|exec)\b"),
    # OS 명령 실행에 자주 쓰이는 특수문자들
    re.compile(r"[;&|`$]"),
]


def sanitize_question(question: str) -> str:
    """
    2차 방어선:
    - 허용된 문자만 남기는 sanitize (앞에서 1차 검증을 했지만,
      안전을 위해 여기서도 한 번 더 필터링 가능)
    """
    # SAFE_QUESTION_REGEX 에서 허용되지 않은 문자는 제거
    # (실제 서비스에서는 로깅을 남겨서 어떤 문자가 제거되었는지 추적하는 것도 좋음)
    sanitized = "".join(ch for ch in question if SAFE_QUESTION_REGEX.match(ch))
    return sanitized


def detect_dangerous_pattern(question: str) -> None:
    """
    질문 문자열에 위험 패턴이 포함되어 있는지 검사.
    발견되면 400 에러를 발생시켜 처리 중단.
    """
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(question):
            raise HTTPException(
                status_code=400,
                detail="허용되지 않는 패턴이 포함된 질문입니다.",
            )


# ---------------------------------------------------------
# 4. 메인 엔드포인트 (/recommend)
# ---------------------------------------------------------
@app.post("/recommend")
def recommend(body: QuestionRequest, user: CurrentUser = Depends(get_current_user)):
    """
    Flask → FastAPI로 호출되는 엔드포인트 예제.
    - body.question : 사용자의 질문 (기본 검증은 Pydantic에서 수행)
    - user.mbr_id   : JWT에서 꺼낸 mbr_id (신뢰 가능)
    """

    # 1) 인증 완료된 사용자 ID
    mbr_id = user.mbr_id

    # 2) 1차 검증(길이/허용문자)은 QuestionRequest에서 이미 수행됨
    question_raw = body.question

    # 3) 2차: 위험 패턴 탐지 (Injection-ish 패턴 차단)
    detect_dangerous_pattern(question_raw)

    # 4) 3차: sanitize (허용 문자만 남기거나, 정책에 따라 변형)
    question_safe = sanitize_question(question_raw)

    # 5) LLM/RAG 호출 시 Prompt Injection 방어용 JSON 래핑 예시
    #    - 실제 LLM 호출 코드에서 이 wrapped_question을 system prompt 내부에
    #      "외부 입력 블록"으로만 사용하도록 설계하면 인젝션 위험을 더 줄일 수 있음.
    wrapped_question = json.dumps(
        {"question": question_safe},
        ensure_ascii=False,
    )

    print(f"[FastAPI] mbr_id={mbr_id}, question_raw={question_raw}, question_safe={question_safe}")

    # TODO: 실제 추천 로직 (LLM/RAG 등)에서 wrapped_question을 활용
    # 예시:
    # answer = call_llm_recommend(mbr_id, wrapped_question, context=...)

    dummy_answer = (
        f"[mbr_id={mbr_id}] 님의 질문은 '{question_safe}' 입니다. "
        f"(여기에 추천 로직 구현)"
    )

    return {
        "mbr_id": mbr_id,
        "question": question_safe,
        "wrapped_question": wrapped_question,  # 디버깅/검증용으로 응답에 포함 (실서비스에서는 제거 가능)
        "answer": dummy_answer,
    }


# ---------------------------------------------------------
# 5. 글로벌 예외 핸들러 (한글 메시지 + JSON 응답)
# ---------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    # 실제 서비스에서는 여기서 로깅 시스템에 기록하는 것이 좋다.
    # print(f"[ERROR] {request.url} - {repr(exc)}")

    return ORJSONResponse(
        status_code=500,
        content={"detail": "내부 서버 오류가 발생했습니다."},
    )


# ---------------------------------------------------------
# 로컬 실행용 (uvicorn)
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fastapi_server:app", host="0.0.0.0", port=8000, reload=True)
