"""ETL 오케스트레이션 — normalize → timeline → aggregate → (선택) load.

사용 (pipeline/ 디렉터리에서):
    uv run python -m etl.run              # 서울: 로컬 빌드 + 로컬 검증까지
    uv run python -m etl.run --load       # 적재 + 원격 검증까지 (.env 필요)

전국 (원본은 T31, 적재 대상은 로컬 스택):
    IJARI_COVERAGE=전국 IJARI_RAW_DIR=/Volumes/T31/ijari/data/raw \
    SUPABASE_DB_URL=$LOCAL_DB_URL uv run python -m etl.run --load

data/raw/{분기}/ 에 서울 CSV가 없고 zip만 있으면 자동 추출한다 (서울 한정 —
전국 추출은 zip 전체를 T31로 푸는 별도 절차).
"""

import os
import sys
from pathlib import Path

import duckdb

from . import aggregate, normalize, timeline, verify
from .quarters import RAW_DIR, available, to_ord

COVERAGE = os.environ.get("IJARI_COVERAGE", "서울")
BUILD_DB = Path(__file__).resolve().parent.parent / "build" / "etl.duckdb"


def extract_missing() -> None:
    if COVERAGE != "서울":
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from download import extract_sido
    for d in sorted(RAW_DIR.iterdir()):
        if not d.is_dir():
            continue
        if any(COVERAGE in p.name for p in d.glob("*.csv")):
            continue
        for zp in d.glob("*.zip"):
            print(f"{d.name}: zip에서 {COVERAGE} CSV 추출")
            extract_sido(zp, COVERAGE)


def main() -> None:
    extract_missing()
    quarter_csvs = available(COVERAGE)
    if not quarter_csvs:
        sys.exit("data/raw/에 준비된 분기가 없다 — download.py부터 실행할 것")
    latest_ord = max(to_ord(q) for q in quarter_csvs)
    print(f"대상 분기 {len(quarter_csvs)}개: {', '.join(quarter_csvs)}")

    BUILD_DB.parent.mkdir(exist_ok=True)
    con = duckdb.connect(str(BUILD_DB))
    normalize.build(con, quarter_csvs)
    timeline.build(con, latest_ord)
    aggregate.build(con, latest_ord)
    paths = aggregate.export(con, latest_ord, COVERAGE)
    for name, p in paths.items():
        print(f"export: {p.name} ({p.stat().st_size / 2**20:.1f}MB)")
    con.close()

    verify.run_local()

    if "--load" in sys.argv:
        from . import load
        load.load()
        verify.FAIL.clear()
        verify.run_remote()
        if verify.FAIL:
            sys.exit(f"원격 검증 실패: {', '.join(verify.FAIL)}")


if __name__ == "__main__":
    main()
