"""⑦ verify — 검증 쿼리 10종 (phase-2 문서 §7).

local 모드: 적재 전에 DuckDB 산출 테이블로 1~8번을 검사한다.
remote 모드: Supabase에 적재된 실제 테이블로 전부 검사한다 (9번은 게이트
place_key 목록 파일이 있을 때만, 10번은 DB 용량).
"""

import os
import sys
from pathlib import Path

FAIL = []


def check(name: str, ok: bool, detail: str) -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name} — {detail}")
    if not ok:
        FAIL.append(name)


def run_checks(q, places: str, history: str, regions: str) -> None:
    """q(sql) -> list[tuple]. 테이블 이름만 바꿔 local/remote 공용."""
    n_places = q(f"select count(*) from {places}")[0][0]
    check("1 자리 수", 100_000 <= n_places <= 2_000_000,
          f"{n_places:,}곳 (서울 기준 수십만 기대)")

    dist = q(f"select turnover_count, count(*) from {places} group by 1 order by 1")
    mode_at_zero = dist and dist[0][0] == 0 and dist[0][1] == max(c for _, c in dist)
    head = ", ".join(f"{t}회:{c:,}" for t, c in dist[:6])
    check("2 교체 분포", bool(mode_at_zero), f"{head} … (0회가 최빈이어야 정상)")

    orphans = q(f"""select count(*) from {history} h
                    left join {places} p using (place_key) where p.place_key is null""")[0][0]
    check("3 고아 연대기 행", orphans == 0, f"{orphans}건")

    inverted = q(f"""select count(*) from {history}
                     where end_quarter is not null and start_quarter > end_quarter""")[0][0]
    check("4 기간 역전(start>end)", inverted == 0, f"{inverted}건")

    low_pct, misang_pct = q(f"""
        select round(100.0 * count(*) filter (where confidence = 'low') / count(*), 1),
               round(100.0 * count(*) filter (where floor_label = '미상') / count(*), 1)
        from {places}""")[0]
    check("5 confidence=low 비율", abs(float(low_pct) - float(misang_pct)) < 0.1,
          f"low {low_pct}% = 층 미상 {misang_pct}%")

    dong_sum = q(f"""select coalesce(sum(place_count), 0) from {regions}
                     where region_level = 'dong'""")[0][0]
    check("6 dong 집계 합 = 자리 수", dong_sum == n_places, f"{dong_sum:,} vs {n_places:,}")

    print("7 교체 최다 top 10 (눈으로 대조):")
    for r in q(f"""select turnover_count, road_address, floor_label from {places}
                   order by turnover_count desc limit 10"""):
        print(f"      {r[0]:>3}회  {r[1]} ({r[2]}층)")

    mn, mx, bad = q(f"""select min(avg_tenure_months), max(avg_tenure_months),
                        count(*) filter (where avg_tenure_months <= 0)
                        from {places} where avg_tenure_months is not null""")[0]
    check("8 평균 점유 개월 범위", bad == 0 and mn >= 3 and mx <= 42,
          f"{mn}~{mx}개월, 0 이하 {bad}건 (기대 3~42)")


def run_local() -> None:
    import duckdb
    con = duckdb.connect(str(Path(__file__).resolve().parent.parent / "build" / "etl.duckdb"),
                         read_only=True)
    q = lambda sql: con.sql(sql).fetchall()
    run_checks(q, "places_final", "history_final", "regions_final")
    total_mb = sum(f.stat().st_size for f in
                   (Path(__file__).resolve().parent.parent / "build").glob("*.csv")) / 2**20
    print(f"참고  10 용량은 적재 후 확인 — CSV 합계 {total_mb:.0f}MB")
    print("참고  9 게이트 20곳 재조회는 remote 모드에서 수행")


def run_remote() -> None:
    import psycopg
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        q = lambda sql: conn.execute(sql).fetchall()
        run_checks(q, "public.places", "public.place_history", "public.region_stats")

        size = q("select pg_size_pretty(pg_database_size(current_database()))")[0][0]
        print(f"10 DB 용량: {size} (서울만 500MB 미만 기대 — D5 전제)")

        gate = Path(__file__).resolve().parent.parent / "spike" / "gate-keys.txt"
        if gate.exists():
            keys = [k.strip() for k in gate.read_text(encoding="utf-8").splitlines() if k.strip()]
            found = q("select count(*) from public.places where place_key = any(%s)"
                      .replace("%s", "'{" + ",".join(keys) + "}'"))[0][0]
            check("9 게이트 자리 재조회", found == len(keys), f"{found}/{len(keys)}곳 존재")
        else:
            print("참고  9 게이트 재조회 생략 — spike/gate-keys.txt 없음 (한 줄에 place_key 하나)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "local"
    run_local() if mode == "local" else run_remote()
    if FAIL:
        sys.exit(f"검증 실패: {', '.join(FAIL)}")
    print("검증 통과")
