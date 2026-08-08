# DB 용량 실측 — 전국 (2026-08-08)

Phase 5 용량 게이트의 결론 기록. 측정 대상은 로컬 자체 호스팅 스택
(OrbStack: PostGIS 16-3.4 + PostgREST v12 + nginx, 데이터는 T31 외장)이다.

## 적재 규모

| 항목 | 값 |
|---|---|
| 분기 | 12개 (2023Q1~2026Q1, 2025Q3은 포털에 없음) |
| 원본 행 | 분기당 약 240만~280만 행 × 12분기 (17개 시도) |
| 자리(places) | 1,974,943곳 |
| 논리적 점포(구간 병합 후) | 3,923,529개 (ID 재발급 병합 224,873건) |
| data_version | 2026Q1+2026-08-08 |

## DB 용량

| 테이블 | 용량 |
|---|---|
| places | 715MB |
| place_history | 598MB |
| 기타 (region_stats·app_meta·spatial_ref_sys) | 약 8MB |
| **DB 전체** | **1,330MB** |

Supabase 무료 티어(500MB)의 약 2.7배 → 클라우드 유지 시 Pro($25/월) 필요.
비용 때문에 로컬 자체 호스팅으로 전환했다 (2026-08-08 결정).
클라우드 프로젝트에는 서울 데이터(258MB)가 그대로 남아 있다.

## 디스크 (T31 외장, ExFAT)

| 항목 | 값 |
|---|---|
| 원본 CSV (12분기 × 17시도, 추출본) | 16GB — ExFAT에 직접 저장 |
| PGDATA (APFS sparsebundle, 200GB sparse) | 실사용 3.9GB |

ExFAT에는 Postgres 데이터 디렉터리를 둘 수 없어 APFS sparsebundle
(`/Volumes/T31/ijari/ijari-db.sparsebundle` → `/Volumes/IjariDB`)로 우회했다.
재부팅 후에는 `hdiutil attach`로 이미지를 다시 마운트해야 컨테이너가 뜬다.

## 원본 데이터 품질 메모

경기 CSV 3개 분기(2025Q1·Q2·Q4)에 이스케이프 안 된 따옴표가 든 행이
총 6개 있어 추출본에서 수정했다(따옴표 패리티 검사, zip 원본은 보존).
ETL은 방언 고정(`delim=',', quote='"', escape='"'`) + `strict_mode=false`로 읽는다.
