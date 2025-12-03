#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_ssot_from_feature_spec.py

단일 feature_spec YAML 을 입력으로 받아서,
auto_features/{feature_id}/ 아래에 다음 5개 산출물을 생성하는 스크립트.

  1) api.yaml                - OpenAPI 3.x 스펙
  2) db_schema.yaml          - DB 스키마(논리 모델)
  3) rules.yaml              - validation + business_rules
  4) testcases.yaml          - API 테스트케이스 정의
  5) validation_schema.json  - JSON Schema (요청 바디 검증용)

특징(완전 자동 확장형 구조):
- generate_ssot_from_feature_spec.py 는 feature 내용이 바뀌어도 수정할 필요가 없도록 설계.
- feature_spec.yaml 전체를 그대로 LLM에 넘기고,
  각 산출물 종류(kind)에 따라 서로 다른 system/prompt 지시만 사용.
- business_rules, validation, api, db, testcases 등 spec 안에 새 필드가 추가되어도,
  LLM이 spec 전체를 보고 판단하도록 하여 확장성을 확보.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from openai import OpenAI


# ---------------------------------------------------------------------------
# 경로 및 클라이언트 설정
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
AUTO_FEATURES_DIR = BASE_DIR / "auto_features"

# OPENAI_API_KEY 환경변수가 설정되어 있어야 함
client = OpenAI()


# ---------------------------------------------------------------------------
# 유틸 함수
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def save_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def extract_block(text: str) -> str:
    """
    LLM이 ```yaml ...``` / ```json ...``` 같은 코드블럭으로 감쌀 수 있으므로
    해당 블럭 안쪽만 잘라서 반환한다. 없으면 전체 텍스트를 사용.
    """
    import re

    # ```something\n .... \n``` 패턴 탐색
    m = re.search(r"```[a-zA-Z0-9_+-]*\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def call_llm(system: str, prompt: str, model: str = "gpt-4.1-mini") -> str:
    """
    OpenAI Chat Completions 호출 래퍼.
    """
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# 산출물별 LLM 생성 로직
# ---------------------------------------------------------------------------

def generate_artifact(feature_id: str, spec: Dict[str, Any], kind: str) -> Any:
    """
    kind 에 따라 서로 다른 system/prompt 를 사용하여 산출물을 생성한다.

    kind:
      - "api"         -> OpenAPI YAML (dict)
      - "db_schema"   -> DB 스키마 YAML (dict)
      - "rules"       -> rules.yaml (dict)
      - "testcases"   -> testcases.yaml (dict)
      - "validation"  -> validation_schema.json (dict, JSON Schema)
    """
    system_messages = {
        "api": (
            "You are an expert backend/API architect.\n"
            "From a feature specification in YAML, generate a single OpenAPI 3.0/3.1 spec.\n"
            "Always return STRICTLY valid YAML only (no markdown, no extra text)."
        ),
        "db_schema": (
            "You are an expert database designer.\n"
            "From a feature specification in YAML, generate a logical DB schema description in YAML.\n"
            "Use tables/columns/constraints that are implied by the spec (api, validation, business_rules, etc.).\n"
            "Always return STRICTLY valid YAML only."
        ),
        "rules": (
            "You are a backend rules/validation designer.\n"
            "From a feature specification in YAML, generate rules.yaml containing validation and business_rules sections.\n"
            "Unify and normalize all validation and business rules from the spec into a single YAML.\n"
            "Always return STRICTLY valid YAML only."
        ),
        "testcases": (
            "You are a senior QA engineer.\n"
            "From a feature specification in YAML, generate a testcases.yaml file.\n"
            "Include typical success/failure cases AND additional cases required by business_rules (e.g., lock_on_fail, max_fail_count).\n"
            "Each testcase should have id, name, and enough info (request/expected) to be used by API tests.\n"
            "Always return STRICTLY valid YAML only."
        ),
        "validation": (
            "You are an expert in JSON Schema (Draft-07 or later).\n"
            "From a feature specification in YAML, generate a JSON Schema for the request body validation.\n"
            "Use all validation constraints defined or implied by the spec.\n"
            "Always return STRICTLY valid JSON only (no markdown, no comments)."
        ),
    }

    if kind not in system_messages:
        raise ValueError(f"Unknown artifact kind: {kind}")

    system = system_messages[kind]

    # feature_spec 전체를 그대로 넘기고, kind 별 산출물 설명만 다르게 준다.
    spec_yaml = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)

    # kind 별 추가 안내 문구
    if kind == "api":
        extra = (
            "The OpenAPI should:\n"
            "- Have 'paths' with the operations described in the spec.\n"
            "- Use request/response schemas consistent with validation, business_rules, and testcases.\n"
            "- Include proper HTTP status codes and error response schemas (e.g., errorCode fields) if specified.\n"
        )
    elif kind == "db_schema":
        extra = (
            "The DB schema should:\n"
            "- Reflect entities implied by the spec (e.g. user, login history, lock status, etc.).\n"
            "- Include primary keys, unique constraints, and nullable information when clear.\n"
            "- Not invent unrelated tables.\n"
        )
    elif kind == "rules":
        extra = (
            "The rules.yaml should:\n"
            "- Contain 'validation' and 'business_rules' top-level keys.\n"
            "- validation: field-level constraints (type, required, pattern, length, etc.).\n"
            "- business_rules: high-level rules such as max_fail_count, lock_on_fail, errorCode mapping.\n"
        )
    elif kind == "testcases":
        extra = (
            "The testcases.yaml should:\n"
            "- Have 'feature_id' at top-level, and 'testcases' list.\n"
            "- Each testcase entry should at least contain: id, name, and data needed for API tests.\n"
            "- If business_rules mention things like max_fail_count or lock_on_fail,\n"
            "  you MUST include scenarios to cover those rules (e.g. multiple failed attempts leading to locked account).\n"
        )
    else:  # "validation"
        extra = (
            "The JSON Schema should:\n"
            "- Contain type: 'object' at the top level.\n"
            "- Use 'properties' and 'required' fields according to the spec's request body.\n"
            "- Include pattern/format/minLength/maxLength constraints as defined.\n"
        )

    prompt = (
        f"Feature ID: {feature_id}\n\n"
        f"Here is the full feature specification in YAML:\n\n"
        f"{spec_yaml}\n\n"
        f"Now generate ONLY the '{kind}' artifact as described below.\n\n"
        f"{extra}\n"
        f"Return ONLY the final artifact content. Do NOT add explanations.\n"
    )

    raw = call_llm(system, prompt)
    cleaned = extract_block(raw)

    # kind 별 파싱 방식
    if kind == "validation":
        return json.loads(cleaned)
    else:
        return yaml.safe_load(cleaned)


# ---------------------------------------------------------------------------
# 메인 함수
# ---------------------------------------------------------------------------

def main(feature_id: str) -> None:
    #spec_path = BASE_DIR / f"feature_specs/{feature_id}_feature_spec.yaml"
    spec_path = BASE_DIR / f"feature_specs/{feature_id}_feature_spec_add_lock.yaml"
    if not spec_path.exists():
        raise FileNotFoundError(f"feature_spec not found: {spec_path}")

    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("OPENAI_API_KEY 환경 변수가 필요합니다.")

    spec = load_yaml(spec_path)

    out_dir = AUTO_FEATURES_DIR / feature_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) api.yaml
    api_data = generate_artifact(feature_id, spec, kind="api")
    save_yaml(out_dir / "api.yaml", api_data)
    print(f"[OK] api.yaml 생성: {out_dir / 'api.yaml'}")

    # 2) db_schema.yaml
    db_data = generate_artifact(feature_id, spec, kind="db_schema")
    save_yaml(out_dir / "db_schema.yaml", db_data)
    print(f"[OK] db_schema.yaml 생성: {out_dir / 'db_schema.yaml'}")

    # 3) rules.yaml
    rules_data = generate_artifact(feature_id, spec, kind="rules")
    save_yaml(out_dir / "rules.yaml", rules_data)
    print(f"[OK] rules.yaml 생성: {out_dir / 'rules.yaml'}")

    # 4) testcases.yaml
    tc_data = generate_artifact(feature_id, spec, kind="testcases")
    save_yaml(out_dir / "testcases.yaml", tc_data)
    print(f"[OK] testcases.yaml 생성: {out_dir / 'testcases.yaml'}")

    # 5) validation_schema.json
    val_data = generate_artifact(feature_id, spec, kind="validation")
    save_json(out_dir / "validation_schema.json", val_data)
    print(f"[OK] validation_schema.json 생성: {out_dir / 'validation_schema.json'}")

    print(f"\n완료: auto_features/{feature_id}/ 아래에 5개 산출물이 생성되었습니다.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_ssot_from_feature_spec.py <feature_id>")
        sys.exit(1)

    main(sys.argv[1])
