"""②~④ span → merge → judge (phase-2 문서 §5-2~4).

- span: (store_id, place_key)별 등장 분기의 연속 구간. 1개 분기 공백은 데이터
  누락으로 간주해 이어 붙인다. 2개 분기 이상 공백은 별도 구간.
- merge: 같은 자리에서 상호(name_norm)가 같고 구간이 맞닿아 있으면 ID 재발급으로
  보고 하나의 논리적 점포로 병합. span의 1-공백 허용 원칙을 그대로 적용해
  공백 1분기까지(start - end <= 2) 병합한다. 상호가 비어 있으면 병합하지 않는다.
- judge: 자리별·연속 분기쌍(t→t+1)별 turnover += min(ended, started) (D9 보수적).
"""

import duckdb


def build(con: duckdb.DuckDBPyConnection, latest_ord: int) -> None:
    # ② span — gaps & islands. 공백 2분기 이상(qord 차이 >= 3)이면 새 구간
    con.sql("""
    create or replace table spans as
    with marked as (
      select qord, store_id, place_key, name_norm, cat_code, cat_name,
        case when qord - lag(qord) over w >= 3 then 1 else 0 end as brk
      from stores_all
      window w as (partition by store_id, place_key order by qord)
    ),
    islands as (
      select *, sum(brk) over (partition by store_id, place_key order by qord) as island
      from marked
    )
    select store_id, place_key, island,
           min(qord) as start_q, max(qord) as end_q,
           arg_max(name_norm, qord) as name_norm,
           arg_max(cat_code, qord) as cat_code,
           arg_max(cat_name, qord) as cat_name
    from islands
    group by store_id, place_key, island
    """)

    # ③ merge — 같은 자리·같은 상호의 맞닿은 구간을 논리적 점포 하나로
    con.sql("""
    create or replace table logical_stores as
    with named as (select * from spans where name_norm <> ''),
    marked as (
      select *,
        case when start_q - lag(end_q) over w <= 2 then 0 else 1 end as brk
      from named
      window w as (partition by place_key, name_norm order by start_q, end_q)
    ),
    grp as (
      select *, sum(brk) over (partition by place_key, name_norm order by start_q, end_q) as g
      from marked
    )
    select place_key, name_norm,
           min(start_q) as start_q, max(end_q) as end_q,
           arg_max(cat_code, end_q) as cat_code,
           arg_max(cat_name, end_q) as cat_name,
           count(*) as merged_spans
    from grp group by place_key, name_norm, g
    union all
    select place_key, name_norm, start_q, end_q, cat_code, cat_name, 1
    from spans where name_norm = ''
    """)

    n_spans, n_logical = con.sql(
        "select (select count(*) from spans), (select count(*) from logical_stores)"
    ).fetchone()
    print(f"timeline: 구간 {n_spans:,} → 병합 후 논리적 점포 {n_logical:,} "
          f"(ID 재발급 병합 {n_spans - n_logical:,}건)")

    # ④ judge — end_q = latest는 아직 영업 중이므로 ended가 아니다
    con.sql(f"""
    create or replace table place_turnover as
    with ended as (
      select place_key, end_q, count(*) as n_ended
      from logical_stores where end_q < {latest_ord}
      group by place_key, end_q
    ),
    started as (
      select place_key, start_q, count(*) as n_started
      from logical_stores where start_q > 0
      group by place_key, start_q
    )
    select e.place_key,
           sum(least(n_ended, n_started))::int as turnover_count
    from ended e
    join started s on s.place_key = e.place_key and s.start_q = e.end_q + 1
    group by e.place_key
    """)
