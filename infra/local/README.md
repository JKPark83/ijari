# 로컬 자가 호스팅 스택 — 운영 메모

전국 데이터(1.3GB)는 Supabase 무료 티어(500MB)를 넘어서 로컬로 서빙한다.
구성: OrbStack 위 PostGIS 16-3.4(:5433) + PostgREST v12 + nginx(:8000, LAN 노출).
앱(supabase-swift)은 `{url}/rest/v1/…`로 요청하므로 nginx가 `/rest/v1/` → PostgREST로 프록시한다.

## 기동 (재부팅 후)

```bash
# 1) T31의 APFS 이미지 마운트 — ExFAT엔 PGDATA를 못 두므로 sparsebundle 우회
hdiutil attach /Volumes/T31/ijari/ijari-db.sparsebundle   # → /Volumes/IjariDB

# 2) OrbStack 기동 후 스택 올리기
open -a OrbStack
cd infra/local && docker compose up -d
```

## 스키마·권한 적용 순서

초기화 스크립트(`init/01-roles.sh`)는 최초 initdb 때만 롤을 만든다.
스키마는 별도로 적용하고, **클라우드 Supabase가 자동으로 해주는 롤 권한을
`grants.sql`로 수동 부여해야 한다** (빠뜨리면 anon 요청이 42501/401):

```bash
for f in ../../supabase/schema.sql ../../supabase/policies.sql \
         ../../supabase/functions.sql grants.sql; do
  docker exec -i ijari-db psql -U postgres -d ijari -v ON_ERROR_STOP=1 < "$f"
done
docker restart ijari-postgrest   # 함수 추가 후 스키마 캐시 갱신 (PGRST202 방지)
```

## anon JWT 발급 (앱 Config에 넣는 키)

```bash
source .env
python3 gen_jwt.py "$PGRST_JWT_SECRET" anon
```

## 비밀 관리

`.env`(POSTGRES_PASSWORD·AUTHENTICATOR_PASSWORD·PGRST_JWT_SECRET)는 절대
커밋하지 않는다. anon JWT는 공개 가능(RLS + grant가 읽기 전용을 강제).

## 전국 ETL 적재

```bash
cd pipeline
source ../infra/local/.env
IJARI_COVERAGE=전국 IJARI_RAW_DIR=/Volumes/T31/ijari/data/raw \
SUPABASE_DB_URL="postgresql://postgres:${POSTGRES_PASSWORD}@127.0.0.1:5433/ijari" \
uv run python -m etl.run --load
```

주의: T31은 ExFAT이라 파일명이 NFD로 돌아오고(`quarters.py`가 NFC로 정규화),
AppleDouble(`._*`) 파일이 계속 생기며(코드에서 필터), 경기 CSV 일부 분기에
따옴표 깨진 행이 있어 추출본을 수정했다(`docs/capacity.md` 참조).
