"""① normalize — 분기별 CSV를 표준 테이블 stores_all로 (phase-2 문서 §5-1).

좌표 결측·(0,0)과 건물관리번호 결측 행은 버리고 버린 수를 로그로 남긴다.
같은 분기에 store_id가 중복이면 한 행만 남긴다.
"""

import duckdb

from .quarters import to_ord

# 상호 정규화 — 스파이크와 동일 규칙 유지 (법인 접미사 → 특수문자 → 소문자)
NORM = (
    "regexp_replace(regexp_replace("
    "lower(coalesce(상호명,'') || coalesce(지점명,'')), "
    "'\\(주\\)|\\(유\\)|㈜|주식회사|유한회사', '', 'g'), "
    "'[\\s()（）\\-_.,''''\"㈜·&]+', '', 'g')"
)

REQUIRED = ["상가업소번호", "상호명", "건물관리번호", "층정보", "경도", "위도",
            "시도코드", "시군구코드", "행정동코드", "상권업종소분류코드"]

# 원본에 따옴표 이스케이프가 깨진 행이 있어(2025Q1 경기) strict_mode를 끄고,
# 스니퍼가 상호명 속 작은따옴표를 이스케이프로 오검출하는 일(강원)을 막기 위해
# 방언(delim·quote·escape)을 명시로 고정한다.
READ_OPTS = ("header=true, all_varchar=true, union_by_name=true, "
             "strict_mode=false, delim=',', quote='\"', escape='\"'")


def build(con: duckdb.DuckDBPyConnection, quarter_csvs: dict) -> None:
    con.sql("""
    create or replace table stores_all (
      qord smallint, store_id text, name_norm text,
      cat_code text, cat_name text,
      sido_code text, sido_name text, sigungu_code text, sigungu_name text,
      dong_code text, dong_name text, road_address text,
      building_id text, floor_label text, place_key text,
      lng double, lat double
    )""")

    for label, csv_paths in quarter_csvs.items():
        qord = to_ord(label)
        # 시도별 파일 여러 개를 한 번에 읽는다 (전국이면 17개). 컬럼 순서가
        # 파일마다 다를 수 있어 union_by_name으로 이름 기준 결합.
        files = "[" + ", ".join(f"'{p}'" for p in csv_paths) + "]"
        try:
            _load_quarter(con, label, qord, files, READ_OPTS)
        except duckdb.NotImplementedException:
            # 손상 행이 섞인 파일은 병렬 CSV 리더가 거부한다 — 그 분기만 단일 스레드로
            print(f"normalize {label}: 병렬 리더 실패, 단일 스레드로 재시도")
            con.sql(f"delete from stores_all where qord={qord}")
            _load_quarter(con, label, qord, files, READ_OPTS + ", parallel=false")


def _load_quarter(con: duckdb.DuckDBPyConnection, label: str, qord: int,
                  files: str, opts: str) -> None:
    cols = {r[0] for r in con.sql(f"""
    describe select * from read_csv_auto({files}, {opts})
    """).fetchall()}
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        raise RuntimeError(f"{label}: 필수 컬럼 없음 {missing} — 스키마 변경 의심, 중단")

    total, dropped = con.sql(f"""
    select count(*),
           count(*) filter (건물관리번호 is null or trim(건물관리번호) = ''
             or try_cast(경도 as double) is null or try_cast(위도 as double) is null
             or try_cast(경도 as double) = 0)
    from read_csv_auto({files}, {opts})
    """).fetchone()

    con.sql(f"""
    insert into stores_all
    select {qord}, 상가업소번호, {NORM},
           coalesce(상권업종소분류코드, '?'), coalesce(상권업종소분류명, '미분류'),
           시도코드, 시도명, 시군구코드, 시군구명,
           행정동코드, 행정동명,
           coalesce(nullif(도로명주소,''), nullif(지번주소,''), ''),
           건물관리번호,
           coalesce(nullif(trim(층정보),''), '미상'),
           건물관리번호 || '#' || coalesce(nullif(trim(층정보),''),'미상'),
           try_cast(경도 as double), try_cast(위도 as double)
    from read_csv_auto({files}, {opts})
    where 건물관리번호 is not null and trim(건물관리번호) <> ''
      and try_cast(경도 as double) is not null and try_cast(위도 as double) is not null
      and try_cast(경도 as double) <> 0
    qualify row_number() over (partition by 상가업소번호) = 1
    """)
    kept = con.sql(f"select count(*) from stores_all where qord={qord}").fetchone()[0]
    print(f"normalize {label}: {total:,}행 중 결측 {dropped:,} 제외, 중복 정리 후 {kept:,}행")
