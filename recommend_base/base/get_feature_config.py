# get_feature_config.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import yaml

# ssot_index.yaml 이 있는 디렉토리 (보통 RECOMMEND_BASE/base)
BASE_DIR = Path(__file__).resolve().parent
SSOT_INDEX_PATH = BASE_DIR / "ssot_index.yaml"


def load_ssot_index() -> Dict[str, Any]:
    """ssot_index.yaml 전체 로드."""
    if not SSOT_INDEX_PATH.exists():
        raise FileNotFoundError(f"ssot_index.yaml not found at {SSOT_INDEX_PATH}")
    return yaml.safe_load(SSOT_INDEX_PATH.read_text(encoding="utf-8"))


def get_feature_config(feature_id: str) -> Dict[str, Any]:
    """
    feature_id(login, signup 등)에 해당하는 설정 블록 반환.
    예: index["features"]["login"]
    """
    index = load_ssot_index()
    features = index.get("features", {})
    if feature_id not in features:
        raise KeyError(f"Feature '{feature_id}' not found in ssot_index.yaml")
    return features[feature_id]


def resolve_path(rel_path: str) -> Path:
    """
    ssot_index.yaml 에 적힌 상대 경로를 실제 파일 경로(Path)로 변환.
    예: 'features/login/api.yaml' → BASE_DIR / 'features/login/api.yaml'
    """
    return (BASE_DIR / rel_path).resolve()


if __name__ == "__main__":
    # 간단 테스트용
    cfg = get_feature_config("login")
    print("login feature config:")
    for k, v in cfg.items():
        print(f"  {k}: {v}")
