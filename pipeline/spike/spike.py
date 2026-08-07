"""Phase 1 데이터 스파이크 — 서울 2023Q1 vs 2026Q1 자리 대조.

산출물 (pipeline/spike/ 아래):
    spike.duckdb   — stores_* / place_diff 테이블 (탐색용)
    health.md      — 서울 데이터 건강 수치 (phase-1 문서 §4)
    samples.csv    — 자리 단위 대조 결과 전체
    report/        — index.html(요약) + 구별 검색 페이지 (상호명 노출: 로컬 검증 전용)

주의: 두 분기 diff이므로 판정 기준은 ID가 아니라 정규화 상호의 생존이다 (문서 §3-2).
"""

import html
import json
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
RAW = HERE.parent.parent / "data" / "raw"
QUARTERS = {"2023Q1": "202303", "2026Q1": "202603"}  # 라벨 → 파일 기준월(YYYYMM)
A, B = "2023Q1", "2026Q1"

con = duckdb.connect(str(HERE / "spike.duckdb"))

# 상호 정규화: 법인 접미사 제거 → 공백·특수문자 제거 → 소문자화.
# '(주)' 를 먼저 지우지 않으면 괄호만 벗겨져 '파크이앤씨주' != '파크이앤씨' 오판이 난다.
NORM = (
    "regexp_replace(regexp_replace("
    "lower(coalesce(상호명,'') || coalesce(지점명,'')), "
    "'\\(주\\)|\\(유\\)|㈜|주식회사|유한회사', '', 'g'), "
    "'[\\s()（）\\-_.,''''\"㈜·&]+', '', 'g')"
)


def normalize() -> None:
    for label in QUARTERS:
        con.sql(f"""
        create or replace table stores_{label} as
        select
          상가업소번호 as store_id,
          {NORM} as name_norm,
          coalesce(nullif(상호명,''),'(상호없음)')
            || coalesce(' ' || nullif(지점명,''), '') as name_raw,
          상권업종대분류명 as cat_top, 상권업종소분류코드 as cat_code, 상권업종소분류명 as cat_name,
          시군구명 as sigungu, 행정동명 as dong, 도로명주소 as road_address,
          건물관리번호 as building_id,
          coalesce(nullif(trim(층정보),''), '미상') as floor_label,
          건물관리번호 || '#' || coalesce(nullif(trim(층정보),''),'미상') as place_key,
          try_cast(경도 as double) as lng, try_cast(위도 as double) as lat
        from read_csv_auto('{RAW}/{label}/*서울*.csv', header=true, all_varchar=true)
        where 건물관리번호 is not null
        """)
        n = con.sql(f"select count(*) from stores_{label}").fetchone()[0]
        print(f"normalize {label}: {n:,}행")


def diff() -> None:
    con.sql(f"""
    create or replace table place_diff as
    with a as (
      select place_key,
             any_value(road_address) as road_address, any_value(sigungu) as sigungu,
             any_value(dong) as dong, any_value(floor_label) as floor_label,
             list(distinct name_norm) filter (name_norm <> '') as names_a,
             list(distinct name_raw || ' · ' || coalesce(cat_name,'?')) as display_a,
             count(*) as n_a
      from stores_{A} group by place_key),
    b as (
      select place_key,
             any_value(road_address) as road_address, any_value(sigungu) as sigungu,
             any_value(dong) as dong, any_value(floor_label) as floor_label,
             list(distinct name_norm) filter (name_norm <> '') as names_b,
             list(distinct name_raw || ' · ' || coalesce(cat_name,'?')) as display_b,
             count(*) as n_b
      from stores_{B} group by place_key)
    select
      coalesce(a.place_key, b.place_key) as place_key,
      coalesce(a.road_address, b.road_address) as road_address,
      coalesce(a.sigungu, b.sigungu) as sigungu,
      coalesce(a.dong, b.dong) as dong,
      coalesce(a.floor_label, b.floor_label) as floor_label,
      a.n_a, b.n_b, a.display_a, b.display_b,
      len(list_intersect(a.names_a, b.names_b)) as survived,
      case
        when a.place_key is null then '신규 자리'
        when b.place_key is null then '자리 소멸(공실 후보)'
        when len(coalesce(a.names_a,[])) = 0 or len(coalesce(b.names_b,[])) = 0
          then '판정 곤란(상호 결측)'
        when len(list_intersect(a.names_a, b.names_b)) = 0 then '전원 교체'
        when len(list_intersect(a.names_a, b.names_b)) < len(a.names_a) then '일부 교체'
        else '유지'
      end as verdict
    from a full join b using (place_key)
    """)
    con.sql(f"copy place_diff to '{HERE}/samples.csv' (format csv, header true)")


def health() -> str:
    lines = ["# 서울 데이터 건강 체크 (Phase 1)\n"]
    lines.append("| 항목 | " + " | ".join(QUARTERS) + " |")
    lines.append("|---|" + "---|" * len(QUARTERS))

    metrics: dict[str, list[str]] = {}
    for label, yyyymm in QUARTERS.items():
        src = f"read_csv_auto('{RAW}/{label}/*서울*.csv', header=true, all_varchar=true)"
        row = con.sql(f"""
        select count(*) as total,
          count(*) filter (건물관리번호 is null or trim(건물관리번호)='') as no_bld,
          count(*) filter (층정보 is null or trim(층정보)='') as no_floor,
          count(*) filter (호정보 is null or trim(호정보)='') as no_ho,
          count(*) filter (substr(상가업소번호,7,6) ~ '^\\d{{6}}$'
                           and substr(상가업소번호,7,6) > '{yyyymm}') as future_id,
          count(*) filter (try_cast(경도 as double) is null or try_cast(위도 as double) is null
                           or try_cast(경도 as double) = 0) as bad_coord
        from {src}
        """).fetchone()
        total, no_bld, no_floor, no_ho, future_id, bad_coord = row
        pct = lambda x: f"{x/total*100:.1f}%"
        metrics.setdefault("전체 행 수", []).append(f"{total:,}")
        metrics.setdefault("건물관리번호 결측", []).append(pct(no_bld))
        metrics.setdefault("층정보 결측", []).append(pct(no_floor))
        metrics.setdefault("호정보 결측", []).append(pct(no_ho))
        metrics.setdefault("ID 날짜 오염(기준월 이후)", []).append(pct(future_id))
        metrics.setdefault("좌표 결측·0", []).append(pct(bad_coord))

        q50, q95, mx = con.sql(f"""
        select median(c), quantile_cont(c, 0.95), max(c)
        from (select count(*) c from stores_{label} group by place_key)
        """).fetchone()
        metrics.setdefault("자리당 점포 수 중앙값", []).append(f"{q50:.0f}")
        metrics.setdefault("자리당 점포 수 95분위", []).append(f"{q95:.0f}")
        metrics.setdefault("자리당 점포 수 최대", []).append(f"{mx:,}")

    for name, vals in metrics.items():
        lines.append(f"| {name} | " + " | ".join(vals) + " |")

    lines.append("\n## 판정 분포 (자리 단위, 2023Q1 → 2026Q1)\n")
    lines.append("| 판정 | 자리 수 | 비율 |")
    lines.append("|---|---|---|")
    total_places = con.sql("select count(*) from place_diff").fetchone()[0]
    for verdict, cnt in con.sql(
        "select verdict, count(*) from place_diff group by 1 order by 2 desc"
    ).fetchall():
        lines.append(f"| {verdict} | {cnt:,} | {cnt/total_places*100:.1f}% |")
    lines.append(f"| (합계) | {total_places:,} | 100% |")

    lines.append("""
## 판독 주의

- **호정보가 100% 결측**이라 자리키는 계획대로 건물관리번호#층이 최대 해상도다.
- 층정보 결측(31~37%)은 '미상' 층으로 묶인다. 고속터미널(신반포로 200) 같은
  대형 건물은 미상 층 하나에 500개+ 점포가 몰린다 — 뷰에서 별도 처리 필요.
- 상호 대조는 정규화 후 완전 일치 기준이라 **리브랜딩·법인명 변경**
  ('제이엠파트너스' → '제이엠파트너스 코리아')은 전원 교체로 오판된다.
  전원 교체 9.5%에는 이런 노이즈가 일부 섞여 있다.
- ID 날짜 오염 0% — 2023Q1 이후 아카이브는 깨끗하다 (시작 분기 결정 뒷받침).
""")

    text = "\n".join(lines) + "\n"
    (HERE / "health.md").write_text(text, encoding="utf-8")
    return text


PAGE_CSS = """
:root{color-scheme:light dark}
body{font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;margin:1.5rem;line-height:1.6;word-break:keep-all}
table{border-collapse:collapse;width:100%;font-size:.85rem}
th,td{border:1px solid #8884;padding:.3rem .5rem;text-align:left;vertical-align:top}
input{width:100%;padding:.5rem;font-size:1rem;margin:.8rem 0;box-sizing:border-box}
.v유지{color:#1baf7a}.v전원교체{color:#d03b3b;font-weight:bold}.v일부교체{color:#eda100}
small{color:#888}
"""


def report() -> None:
    out = HERE / "report"
    out.mkdir(exist_ok=True)
    total = con.sql("select count(*) from place_diff").fetchone()[0]
    verdicts = con.sql(
        "select verdict, count(*) from place_diff group by 1 order by 2 desc"
    ).fetchall()
    gus = [r[0] for r in con.sql(
        "select distinct sigungu from place_diff where sigungu is not null order by 1"
    ).fetchall()]

    rows_v = "".join(
        f"<tr><td>{html.escape(v)}</td><td>{c:,}</td><td>{c/total*100:.1f}%</td></tr>"
        for v, c in verdicts)
    links = " · ".join(f'<a href="{html.escape(g)}.html">{html.escape(g)}</a>' for g in gus)
    (out / "index.html").write_text(f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>스파이크 리포트 — 서울 {A} vs {B}</title><style>{PAGE_CSS}</style></head><body>
<h1>스파이크 리포트 — 서울 {A} vs {B}</h1>
<p><strong>⚠️ gate-list.md에 20곳을 먼저 적었는가?</strong> 아직이면 이 리포트를 닫고 목록부터 쓸 것 (기억 오염 방지).</p>
<h2>판정 분포 (자리 {total:,}곳)</h2>
<table><tr><th>판정</th><th>자리 수</th><th>비율</th></tr>{rows_v}</table>
<h2>구별 검색 페이지</h2><p>{links}</p>
<p><small>상호명이 그대로 보이는 로컬 검증 도구다 — 공유·커밋 금지. 앱과 DB에는 상호명이 들어가지 않는다.</small></p>
</body></html>""", encoding="utf-8")

    for gu in gus:
        rows = con.sql("""
        select road_address, floor_label, coalesce(n_a,0), coalesce(n_b,0),
               coalesce(display_a,[]), coalesce(display_b,[]), verdict
        from place_diff where sigungu = ? order by road_address, floor_label
        """, params=[gu]).fetchall()
        data = [[r[0] or "", r[1], r[2], r[3], " / ".join(r[4]), " / ".join(r[5]), r[6]]
                for r in rows]
        (out / f"{gu}.html").write_text(f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>{html.escape(gu)} — 자리 대조</title><style>{PAGE_CSS}</style></head><body>
<h1>{html.escape(gu)} <small>자리 {len(data):,}곳</small></h1>
<input id="q" placeholder="도로명주소·상호로 검색 (2글자 이상)" autofocus>
<table><thead><tr><th>도로명주소</th><th>층</th><th>{A} 점포</th><th>{B} 점포</th><th>판정</th></tr></thead>
<tbody id="tb"></tbody></table>
<p><small id="cnt"></small></p>
<script>
const D={json.dumps(data, ensure_ascii=False)};
const tb=document.getElementById('tb'),cnt=document.getElementById('cnt'),esc=s=>s.replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
function render(q){{
  const m=q.length>=2?D.filter(r=>(r[0]+r[4]+r[5]).includes(q)):D.slice(0,200);
  tb.innerHTML=m.slice(0,300).map(r=>`<tr><td>${{esc(r[0])}}</td><td>${{esc(r[1])}}</td><td>${{esc(r[4])}} <small>(${{r[2]}})</small></td><td>${{esc(r[5])}} <small>(${{r[3]}})</small></td><td class="v${{r[6].replace(/[^가-힣]/g,'')}}">${{esc(r[6])}}</td></tr>`).join('');
  cnt.textContent=q.length>=2?`${{m.length}}곳 일치 (최대 300곳 표시)`:`검색 전 — 앞 200곳만 표시`;
}}
document.getElementById('q').addEventListener('input',e=>render(e.target.value.trim()));
render('');
</script></body></html>""", encoding="utf-8")
    print(f"report: {out}/index.html + 구별 {len(gus)}개 페이지")


if __name__ == "__main__":
    normalize()
    diff()
    print(health())
    report()
