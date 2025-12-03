# ⭐ SSOT + SDD 기반 자동 개발 파이프라인

# 📌 프로젝트 개요

이 프로젝트는 **SSOT(Single Source of Truth)** 와  
**SDD(Specification-Driven Development)** 개념을 기반으로 한다.

- 사람이 작성하는 스펙은 **오직 1개의 feature_spec.yaml**
- LLM(OpenAI API)을 이용해  
  - API 스펙  
  - DB 스키마  
  - Validation 규칙  
  - 비즈니스 룰  
  - 테스트 케이스  
  **5개 SSOT 파일을 자동 생성**
- 이어서 LLM으로  
  - FastAPI API 코드  
  - DB SQL  
  - Flask UI 코드  
  - Pytest 테스트 코드  
  **실행 가능한 코드까지 자동 생성**

즉,

> **“스펙만 작성하면 나머지는 자동으로 생성되는 구조(SDD)”**

를 목표로 한다.

---

# 📁 디렉토리 구조

```bash
prj_home/
│
├── auto_features/                      # ← SSOT feature_spec → 자동 생성된 1차 산출물
│   └── {feature_id}/
│       ├── api.yaml
│       ├── db_schema.yaml
│       ├── rules.yaml
│       ├── testcases.yaml
│       └── validation_schema.json
│
├── base/
│   ├── features/                       # ← 사람이 관리 + 자동생성 결과 저장
│   │   └── {feature_id}/
│   │       ├── design/
│   │       │   ├── components.json
│   │       │   ├── flow.json
│   │       │   └── tokens.json
│   │       ├── api.yaml
│   │       ├── db_schema.yaml
│   │       ├── rules.yaml
│   │       ├── testcases.yaml
│   │       └── validation_schema.json
│   │
│   ├── generated/                      # ← 최종 실행 가능한 코드가 생성되는 디렉토리
│   │   └── {feature_id}/
│   │       ├── api/
│   │       │   └── {feature_id}_api.py
│   │       ├── ui/
│   │       │   └── {feature_id}_ui.py
│   │       ├── db/
│   │       │   └── {feature_id}_schema.sql
│   │       └── test/
│   │           └── {feature_id}_test.py
│   │
│   ├── prompts/                        # ← LLM 코드 생성용 프롬프트 템플릿
│   │   └── {feature_id}/
│   │       ├── api.prompt
│   │       ├── ui.prompt
│   │       ├── test.prompt
│   │       └── db.prompt
│   │
│   ├── generate_all.py                 # ← api/ui/db/test 코드 전체 생성기
│   ├── get_feature_config.py           # ← feature_id별 경로 매핑
│   ├── lint_ssot.py                    # ← SSOT 파일(5종) 검증기
│   └── ssot_index.yaml                 # ← 모든 feature들의 경로 인덱스
│
├── feature_specs/                      # ← SSOT 원본 스펙(사람이 작성)
│   └── {feature_id}_feature_spec.yaml
│
├── generate_ssot_from_feature_spec.py  # ← feature_spec → auto_features 변환기
└── README.md
```

---

# 🚀 전체 개발 흐름(SSOT → SDD)

## 1단계. 기능 스펙 작성
→ feature_specs/{feature_id}_feature_spec.yaml

## 2단계. SSOT 5종 자동 생성
```bash
python generate_ssot_from_feature_spec.py login
```

## 3단계. base/features로 반영

## 4단계. 실행 코드 자동 생성
```bash
python base/generate_all.py login
```

---

# 🔥 장점 요약

- 변경 시 **feature_spec.yaml만 수정하면 됨**
- API/DB/UI/TEST 일관성 자동 유지
- 반복작업 제거 → 개발자는 핵심 로직에 집중
- 기능 추가 시 즉시 확장 가능

---

