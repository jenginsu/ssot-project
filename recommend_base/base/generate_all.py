# generate_all.py
"""
SSOT 기반 코드/테스트/DB/UI 자동 생성기

사용방법 예시:
  python generate_all.py login
  python generate_all.py login --modes api ui
  python generate_all.py --all
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml
from openai import OpenAI

from get_feature_config import get_feature_config, resolve_path, load_ssot_index

BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"

client = OpenAI()  # OPENAI_API_KEY 환경변수 필요


# ---------------------------------------------------------------------
# 유틸 함수들
# ---------------------------------------------------------------------
def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_yaml_str(path: Path) -> str:
    """LLM에 그대로 넘기기 좋게 YAML을 문자열로 읽는다."""
    return path.read_text(encoding="utf-8")


def load_json_str(path: Path) -> str:
    """LLM에 그대로 넘기기 좋게 JSON을 pretty string 으로 변환."""
    obj = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(obj, ensure_ascii=False, indent=2)


def call_llm(
    prompt: str,
    system: str = "너는 SSOT 기반으로 코드를 생성하는 어시스턴트다.",
) -> str:
    """OpenAI ChatCompletion 호출."""
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def extract_code_block(text: str, language: str | None = None) -> str:
    """
    LLM이 반환한 텍스트에서 코드블록만 추출.

    - language 가 주어지면 ```{language} ... ``` 구간만 추출
    - 없으면 첫 번째 ``` ... ``` 블록을 추출
    - 아무 코드블록이 없으면 원본 전체를 반환 (fallback)
    """
    if language:
        pattern = rf"```{re.escape(language)}\s*(.*?)(```|$)"
    else:
        pattern = r"```[a-zA-Z0-9_+-]*\s*(.*?)(```|$)"

    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # 코드블록이 없다면 그냥 전체 텍스트 사용
    return text.strip()


# ---------------------------------------------------------------------
# 각 모드별 생성 함수
# ---------------------------------------------------------------------
def generate_api(feature_id: str, cfg: Dict[str, Any]) -> None:
    print(f"[GENERATE] API for feature={feature_id}")

    prompt_path = resolve_path(cfg["prompts"]["api"])
    prompt_tpl = load_text(prompt_path)

    api_spec_str = load_yaml_str(resolve_path(cfg["api_spec"]))
    rules_str = load_yaml_str(resolve_path(cfg["rules"]))
    validation_str = load_json_str(resolve_path(cfg["validation"]))
    db_schema_str = load_yaml_str(resolve_path(cfg["db_schema"]))
    testcases_str = load_yaml_str(resolve_path(cfg["testcases"]))

    prompt = prompt_tpl.format(
        feature_id=feature_id,
        api_spec=api_spec_str,
        rules=rules_str,
        validation_schema=validation_str,
        db_schema=db_schema_str,
        testcases=testcases_str,
    )

    raw = call_llm(prompt)
    code = extract_code_block(raw, language="python")  # 파이썬 코드만 추출

    # generated/<feature>/api/<feature>_api.py
    out_dir = GENERATED_DIR / feature_id / "api"
    ensure_dir(out_dir)
    out_path = out_dir / f"{feature_id}_api.py"
    out_path.write_text(code, encoding="utf-8")
    print(f"  → {out_path} 생성 완료")


def generate_ui(feature_id: str, cfg: Dict[str, Any]) -> None:
    print(f"[GENERATE] UI for feature={feature_id}")

    prompt_path = resolve_path(cfg["prompts"]["ui"])
    prompt_tpl = load_text(prompt_path)

    design_cfg = cfg.get("design", {})
    components_str = ""
    flow_str = ""
    tokens_str = ""

    if "components" in design_cfg:
        components_str = load_json_str(resolve_path(design_cfg["components"]))
    if "flow" in design_cfg:
        flow_str = load_json_str(resolve_path(design_cfg["flow"]))
    if "tokens" in design_cfg:
        tokens_str = load_json_str(resolve_path(design_cfg["tokens"]))

    rules_str = load_yaml_str(resolve_path(cfg["rules"]))
    validation_str = load_json_str(resolve_path(cfg["validation"]))

    prompt = prompt_tpl.format(
        feature_id=feature_id,
        components=components_str,
        flow=flow_str,
        tokens=tokens_str,
        rules=rules_str,
        validation_schema=validation_str,
    )

    raw = call_llm(prompt)

    # UI 생성 결과가 Flask(Python) 코드라면:
    code = extract_code_block(raw, language="python")
    # 만약 HTML 템플릿을 생성하도록 프롬프트를 짰다면 language="html" 로 변경.

    out_dir = GENERATED_DIR / feature_id / "ui"
    ensure_dir(out_dir)
    out_path = out_dir / f"{feature_id}_ui.py"
    out_path.write_text(code, encoding="utf-8")
    print(f"  → {out_path} 생성 완료")


def generate_test(feature_id: str, cfg: Dict[str, Any]) -> None:
    print(f"[GENERATE] TEST for feature={feature_id}")

    prompt_path = resolve_path(cfg["prompts"]["test"])
    prompt_tpl = load_text(prompt_path)

    api_spec_str = load_yaml_str(resolve_path(cfg["api_spec"]))
    testcases_str = load_yaml_str(resolve_path(cfg["testcases"]))
    validation_str = load_json_str(resolve_path(cfg["validation"]))
    rules_str = load_yaml_str(resolve_path(cfg["rules"]))

    prompt = prompt_tpl.format(
        feature_id=feature_id,
        api_spec=api_spec_str,
        testcases=testcases_str,
        validation_schema=validation_str,
        rules=rules_str,
    )

    raw = call_llm(prompt)
    code = extract_code_block(raw, language="python")  # pytest 코드만 추출

    out_dir = GENERATED_DIR / feature_id / "test"
    ensure_dir(out_dir)
    out_path = out_dir / f"{feature_id}_test.py"
    out_path.write_text(code, encoding="utf-8")
    print(f"  → {out_path} 생성 완료")


def generate_db(feature_id: str, cfg: Dict[str, Any]) -> None:
    print(f"[GENERATE] DB for feature={feature_id}")

    prompt_path = resolve_path(cfg["prompts"]["db"])
    prompt_tpl = load_text(prompt_path)

    db_schema_str = load_yaml_str(resolve_path(cfg["db_schema"]))
    rules_str = load_yaml_str(resolve_path(cfg["rules"]))

    prompt = prompt_tpl.format(
        feature_id=feature_id,
        db_schema=db_schema_str,
        rules=rules_str,
    )

    raw = call_llm(prompt)
    sql = extract_code_block(raw, language="sql")  # SQL 코드만 추출

    out_dir = GENERATED_DIR / feature_id / "db"
    ensure_dir(out_dir)
    out_path = out_dir / f"{feature_id}_schema.sql"
    out_path.write_text(sql, encoding="utf-8")
    print(f"  → {out_path} 생성 완료")


# ---------------------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------------------
def generate_for_feature(feature_id: str, modes: List[str]) -> None:
    cfg = get_feature_config(feature_id)

    if "api" in modes:
        generate_api(feature_id, cfg)
    if "ui" in modes:
        generate_ui(feature_id, cfg)
    if "test" in modes:
        generate_test(feature_id, cfg)
    if "db" in modes:
        generate_db(feature_id, cfg)


def main() -> None:
    parser = argparse.ArgumentParser(description="SSOT 기반 코드/테스트/DB 자동 생성기")
    parser.add_argument(
        "feature",
        nargs="?",
        help="생성할 feature ID (예: login, signup). 생략하면 --all 필요.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="모든 feature 대상 생성",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["api", "ui", "test", "db"],
        default=["api", "ui", "test", "db"],
        help="생성할 대상 (기본: api ui test db 모두)",
    )

    args = parser.parse_args()

    if not args.all and not args.feature:
        parser.error("feature 또는 --all 중 하나는 지정해야 합니다.")

    if args.all:
        index = load_ssot_index()
        features = list(index.get("features", {}).keys())
    else:
        features = [args.feature]

    print("=== GENERATE START ===")
    print(f"features: {features}")
    print(f"modes   : {args.modes}")
    print("======================")

    for fid in features:
        generate_for_feature(fid, args.modes)

    print("=== GENERATE DONE ===")


if __name__ == "__main__":
    main()
