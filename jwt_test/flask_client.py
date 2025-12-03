# flask_client.py
import json
from flask import Flask, Response
import requests
import jwt  # pip install pyjwt

from config_auth import SECRET_KEY, ALGORITHM

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

FASTAPI_RECOMMEND_URL = "http://localhost:8000/recommend"  # FastAPI 엔드포인트


def create_access_token(mbr_id: str) -> str:
    payload = {"sub": mbr_id}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


@app.route("/ask", methods=["GET"])
def ask_recommend():
    # 하드코딩
    mbr_id = "user123"
    question = "키보드 추천해줘"

    if not mbr_id or not question:
        return Response(
            json.dumps({"error": "mbr_id and question are required"}, ensure_ascii=False),
            status=400,
            content_type="application/json; charset=utf-8",
        )

    access_token = create_access_token(mbr_id)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "question": question
    }

    try:
        resp = requests.post(
            FASTAPI_RECOMMEND_URL,
            json=payload,
            headers=headers,
            timeout=5,
        )

        # 🔥 FastAPI에서 온 JSON을 다시 jsonify 하지 말고, 그대로 전달
        return Response(
            resp.content,                            # 원본 바이트 그대로
            status=resp.status_code,
            content_type=resp.headers.get(
                "Content-Type", "application/json"
            ),
        )

    except Exception as e:
        return Response(
            json.dumps({"error": f"FastAPI 호출 실패: {repr(e)}"}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
