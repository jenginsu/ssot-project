# lint_ssot.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Iterable

import yaml

#from get_feature_config import get_feature_config, resolve_path, load_ssot_index
from get_feature_config import resolve_path, load_ssot_index


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_files_exist(feature_id: str, cfg: Dict[str, Any]) -> None:
    print(f"\n[CHECK] feature = {feature_id} :: 파일 존재 여부 확인")

    paths_to_check: Iterable[tuple[str, str]] = [
        ("api_spec", cfg.get("api_spec")),
        ("validation", cfg.get("validation")),
        ("rules", cfg.get("rules")),
        ("testcases", cfg.get("testcases")),
        ("db_schema", cfg.get("db_schema")),
    ]

    design_cfg = cfg.get("design", {})
    for dk in ("components", "flow", "tokens"):
        if dk in design_cfg:
            paths_to_check.append((f"design.{dk}", design_cfg[dk]))

    prompts_cfg = cfg.get("prompts", {})
    for pk, rel in prompts_cfg.items():
        paths_to_check.append((f"prompts.{pk}", rel))

    for label, rel_path in paths_to_check:
        if not rel_path:
            print(f"  - {label}: 경로 없음 (ssot_index.yaml에서 누락)")
            continue
        p = resolve_path(rel_path)
        print(f"  - {label}: {p}", end="")
        if p.exists():
            print("  ✅")
        else:
            print("  ❌ (파일 없음)")


def lint_api_vs_validation(feature_id: str, cfg: Dict[str, Any]) -> None:
    """
    api.yaml 의 requestBody 필드 vs validation_schema.json 의 properties 비교.
    """
    api_path = resolve_path(cfg["api_spec"])
    validation_path = resolve_path(cfg["validation"])

    api_spec = load_yaml(api_path)
    validation = load_json(validation_path)

    paths = api_spec.get("paths", {})
    if not paths:
        print(f"\n[WARN] feature={feature_id} api_spec.paths 비어있음")
        return

    # 첫 번째 path + post 기준으로 비교 (단순 버전)
    first_path = next(iter(paths.keys()))
    post_spec = paths[first_path].get("post", {})
    req_body = (
        post_spec.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )

    api_fields = set(req_body.get("properties", {}).keys())
    validation_fields = set(validation.get("properties", {}).keys())

    print(f"\n[CHECK] feature = {feature_id} :: API vs validation_schema 필드 비교")
    print(f"  - path: {first_path}")

    only_in_api = api_fields - validation_fields
    only_in_validation = validation_fields - api_fields

    print(f"  - API only   fields: {sorted(only_in_api) or '없음'}")
    print(f"  - Schema only fields: {sorted(only_in_validation) or '없음'}")


def lint_api_vs_testcases(feature_id: str, cfg: Dict[str, Any]) -> None:
    """
    testcases.yaml 의 input 필드 vs api requestBody 필드 간 대략적인 비교.
    """
    api_path = resolve_path(cfg["api_spec"])
    tc_path = resolve_path(cfg["testcases"])

    api_spec = load_yaml(api_path)
    testcases = load_yaml(tc_path)

    paths = api_spec.get("paths", {})
    if not paths:
        print(f"\n[WARN] feature={feature_id} api_spec.paths 비어있음")
        return

    first_path = next(iter(paths.keys()))
    post_spec = paths[first_path].get("post", {})
    req_body = (
        post_spec.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )

    api_fields = set(req_body.get("properties", {}).keys())

    print(f"\n[CHECK] feature = {feature_id} :: API vs testcases 입력 필드 비교")
    print(f"  - path: {first_path}")

    tcs = testcases.get("testcases", [])
    if not tcs:
        print("  - testcases가 비어있음")
        return

    for tc in tcs:
        tc_id = tc.get("id")
        input_obj = tc.get("input", {})
        tc_fields = set(input_obj.keys())

        missing_in_tc = api_fields - tc_fields
        extra_in_tc = tc_fields - api_fields

        print(f"  - testcase {tc_id}:")
        print(f"      · 누락 필드(API 기준): {sorted(missing_in_tc) or '없음'}")
        print(f"      · 추가 필드(테스트만): {sorted(extra_in_tc) or '없음'}")


def lint_all() -> None:
    index = load_ssot_index()
    features = index.get("features", {})

    if not features:
        print("features 가 ssot_index.yaml 에 없습니다.")
        return

    for fid, cfg in features.items():
        print("\n" + "=" * 60)
        print(f"[FEATURE] {fid}")
        print("=" * 60)
        check_files_exist(fid, cfg)

        # 파일 없으면 이후 검사에서 에러 나므로 존재할 때만 수행
        if cfg.get("api_spec") and cfg.get("validation"):
            try:
                lint_api_vs_validation(fid, cfg)
            except Exception as e:
                print(f"[ERROR] API vs validation 검사 중 예외: {e}")

        if cfg.get("api_spec") and cfg.get("testcases"):
            try:
                lint_api_vs_testcases(fid, cfg)
            except Exception as e:
                print(f"[ERROR] API vs testcases 검사 중 예외: {e}")


if __name__ == "__main__":
    lint_all()
