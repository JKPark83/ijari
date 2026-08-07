"""⑥ load — 단일 트랜잭션 truncate + COPY (phase-2 문서 §6, D8).

Postgres MVCC 덕에 커밋 전까지 앱은 이전 데이터를 계속 읽는다.
geom은 generated column이라 COPY 컬럼 목록에 넣으면 에러 — lat/lng만 보낸다.
연결은 Session pooler(:5432) 문자열(SUPABASE_DB_URL)만 쓴다 (direct는 IPv6 전용).
"""

import datetime
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from .aggregate import BUILD_DIR, HISTORY_COLS, PLACES_COLS, REGION_COLS

COLUMNS = {
    "places": PLACES_COLS,
    "place_history": HISTORY_COLS,
    "region_stats": REGION_COLS,
}


def load() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("SUPABASE_DB_URL 없음 — pipeline/.env를 채운 뒤 다시 실행 (.env.example 참조)")

    meta = dict(line.split("=", 1) for line in
                (BUILD_DIR / "meta.txt").read_text(encoding="utf-8").splitlines() if "=" in line)
    version = f"{meta['latest_quarter']}+{datetime.date.today().isoformat()}"

    with psycopg.connect(db_url) as conn:
        with conn.transaction():
            cur = conn.cursor()
            cur.execute("truncate public.place_history, public.places, public.region_stats")
            for table, cols in COLUMNS.items():
                csv_path = BUILD_DIR / f"{table}.csv"
                with open(csv_path, encoding="utf-8") as f, cur.copy(
                    f"copy public.{table} ({cols}) from stdin (format csv, header true)"
                ) as cp:
                    while data := f.read(1 << 20):
                        cp.write(data)
                print(f"load: {table} ← {csv_path.name}")
            cur.execute("""insert into public.app_meta (key, value) values
                           ('latest_quarter', %s), ('coverage', %s), ('data_version', %s)
                           on conflict (key) do update
                           set value = excluded.value, updated_at = now()""",
                        (meta["latest_quarter"], meta["coverage"], version))
    print(f"load: 커밋 완료 — 앱이 새 데이터를 보기 시작한다 (data_version={version})")


if __name__ == "__main__":
    load()
