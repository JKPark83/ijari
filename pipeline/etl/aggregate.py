"""⑤ aggregate — places · place_history · region_stats 완성 + CSV 내보내기.

- avg_tenure_months: 종료된 논리적 점포만 평균, 분기 × 3개월 (phase-2 문서 §5-5).
- confidence: 층 미상이면 'low'.
- 공실: 마지막 두 분기 연속 점포 0이면 is_occupied=false,
  마지막 한 분기만 0이면 판단 보류(true 유지, stores_current=0).
- current_category: 현재 영업 중인 점포 중 가장 최근 입주한 점포의 업종.
"""

from pathlib import Path

import duckdb

from .quarters import to_label

BUILD_DIR = Path(__file__).resolve().parent.parent / "build"

# load.py의 COPY 컬럼 목록과 1:1 — geom(generated)은 제외
PLACES_COLS = ("place_key, building_id, floor_label, road_address, sido_code, "
               "sigungu_code, dong_code, lat, lng, turnover_count, avg_tenure_months, "
               "confidence, stores_current, is_occupied, current_category_code, "
               "current_category_name, first_quarter, last_quarter")
HISTORY_COLS = "place_key, seq, start_quarter, end_quarter, category_code, category_name, tenure_quarters"
REGION_COLS = ("region_level, region_code, region_name, center_lat, center_lng, "
               "place_count, turnover_sum, turnover_avg, hot_place_count, avg_tenure_months")


def build(con: duckdb.DuckDBPyConnection, latest_ord: int) -> None:
    labels = {q: to_label(q) for q in range(latest_ord + 1)}
    label_case = "case qord " + " ".join(
        f"when {q} then '{lbl}'" for q, lbl in labels.items()) + " end"

    con.sql(f"""
    create or replace table places_final as
    with base as (
      select place_key,
        arg_max(building_id, qord)  as building_id,
        arg_max(floor_label, qord)  as floor_label,
        arg_max(road_address, qord) as road_address,
        arg_max(sido_code, qord)    as sido_code,
        arg_max(sigungu_code, qord) as sigungu_code,
        arg_max(dong_code, qord)    as dong_code,
        arg_max(lat, qord) as lat, arg_max(lng, qord) as lng,
        min(qord) as first_q, max(qord) as last_q,
        count(*) filter (qord = {latest_ord})     as stores_current,
        count(*) filter (qord = {latest_ord} - 1) as stores_prev
      from stores_all group by place_key
    ),
    tenure as (
      select place_key, avg((end_q - start_q + 1) * 3.0) as avg_tenure_months
      from logical_stores where end_q < {latest_ord} group by place_key
    ),
    current_cat as (
      select place_key, arg_max(cat_code, start_q) as code, arg_max(cat_name, start_q) as name
      from logical_stores where end_q = {latest_ord} group by place_key
    )
    select b.place_key, b.building_id, b.floor_label, b.road_address,
           b.sido_code, b.sigungu_code, b.dong_code, b.lat, b.lng,
           coalesce(t.turnover_count, 0) as turnover_count,
           round(te.avg_tenure_months, 1) as avg_tenure_months,
           case when b.floor_label = '미상' then 'low' else 'high' end as confidence,
           b.stores_current,
           not (b.stores_current = 0 and b.stores_prev = 0) as is_occupied,
           c.code as current_category_code, c.name as current_category_name,
           {label_case.replace('qord', 'b.first_q')} as first_quarter,
           {label_case.replace('qord', 'b.last_q')}  as last_quarter
    from base b
    left join place_turnover t using (place_key)
    left join tenure te using (place_key)
    left join current_cat c using (place_key)
    """)

    con.sql(f"""
    create or replace table history_final as
    select place_key,
           row_number() over (partition by place_key order by start_q, end_q, name_norm) as seq,
           {label_case.replace('qord', 'start_q')} as start_quarter,
           case when end_q = {latest_ord} then null
                else {label_case.replace('qord', 'end_q')} end as end_quarter,
           cat_code as category_code, cat_name as category_name,
           (end_q - start_q + 1) as tenure_quarters
    from logical_stores
    """)

    con.sql(f"""
    create or replace table regions_final as
    with names as (
      select 'sido' as lvl, sido_code as code, arg_max(sido_name, qord) as name
      from stores_all group by sido_code
      union all
      select 'sigungu', sigungu_code, arg_max(sigungu_name, qord) from stores_all group by sigungu_code
      union all
      select 'dong', dong_code, arg_max(dong_name, qord) from stores_all group by dong_code
    ),
    keyed as (
      select 'sido' as lvl, sido_code as code, * from places_final
      union all
      select 'sigungu', sigungu_code, * from places_final
      union all
      select 'dong', dong_code, * from places_final
    ),
    stats as (
      select lvl, code,
             avg(lat) as center_lat, avg(lng) as center_lng,
             count(*) as place_count,
             sum(turnover_count) as turnover_sum,
             round(avg(turnover_count), 2) as turnover_avg,
             count(*) filter (turnover_count >= 3) as hot_place_count,
             round(avg(avg_tenure_months), 1) as avg_tenure_months
      from keyed
      group by lvl, code
    )
    select s.lvl as region_level, s.code as region_code,
           coalesce(n.name, s.code) as region_name,
           s.center_lat, s.center_lng, s.place_count,
           s.turnover_sum, s.turnover_avg, s.hot_place_count, s.avg_tenure_months
    from stats s left join names n on n.lvl = s.lvl and n.code = s.code
    """)


def export(con: duckdb.DuckDBPyConnection, latest_ord: int, coverage: str) -> dict:
    BUILD_DIR.mkdir(exist_ok=True)
    outputs = {
        "places": (PLACES_COLS, "places_final", "place_key"),
        "place_history": (HISTORY_COLS, "history_final", "place_key, seq"),
        "region_stats": (REGION_COLS, "regions_final", "region_level, region_code"),
    }
    paths = {}
    for name, (cols, table, order) in outputs.items():
        path = BUILD_DIR / f"{name}.csv"
        con.sql(f"copy (select {cols} from {table} order by {order}) "
                f"to '{path}' (format csv, header true)")
        paths[name] = path
    (BUILD_DIR / "meta.txt").write_text(
        f"latest_quarter={to_label(latest_ord)}\ncoverage={coverage}\n", encoding="utf-8")
    return paths
