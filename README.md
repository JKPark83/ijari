# 이 자리 (ijari)

지도에서 상가 자리를 누르면 그 자리에서 주인이 몇 번 바뀌었는지 보여주는 iOS 앱.
소상공인시장진흥공단 상가(상권)정보 분기 스냅숏을 대조해 자리별 교체 이력을 만든다.

- 계획 문서: `docs/plan/` (원본은 Obsidian `Documents/이 자리 - 상가 교체 연대기 앱 기획/plan/`)
- 진행 체크리스트: Obsidian의 `plan/tasks.md`에서만 체크한다.

## 구조

```
pipeline/   # Python ETL (uv 관리): download → normalize → timeline → aggregate → load → verify
supabase/   # schema.sql · policies.sql · functions.sql
ios/        # XcodeGen project.yml + Ijari/ (Phase 3부터)
data/raw/   # 분기별 원본 CSV/zip — git 제외, 영구 보관 (포털 아카이브를 신뢰하지 않음)
docs/       # 계획 문서 사본, 용량/판정 기록
```

## 시작

```bash
cd pipeline
uv sync
uv run python download.py --list     # 분기 → uddi 매핑 확인
uv run python download.py 2026Q1     # 분기 zip 다운로드
```

스택: Supabase Postgres + PostGIS (앱 직접 질의, 읽기 전용 RLS) · Python + DuckDB ETL · SwiftUI + MapKit (iOS 17+).
