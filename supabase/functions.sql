-- 이 자리 — RPC 3종 (phase-2 문서 §4)
-- 전부 security invoker(기본값) 유지 — anon 권한으로 실행되어 RLS가 그대로 적용된다.

-- 줌인: 화면 사각형 안의 자리. 교체 많은 순, 상한 필수
create or replace function public.map_places(
  min_lng float8, min_lat float8, max_lng float8, max_lat float8,
  min_turnover int default 0, max_rows int default 500
) returns setof public.places
language sql stable as $$
  select * from public.places
  where geom && st_makeenvelope(min_lng, min_lat, max_lng, max_lat, 4326)
    and turnover_count >= min_turnover
  order by turnover_count desc
  limit least(greatest(max_rows, 1), 1000);
$$;

-- 줌아웃: 화면 안의 지역 마커
create or replace function public.map_regions(
  p_level text, min_lng float8, min_lat float8, max_lng float8, max_lat float8
) returns setof public.region_stats
language sql stable as $$
  select * from public.region_stats
  where region_level = p_level
    and center_lng between min_lng and max_lng
    and center_lat between min_lat and max_lat;
$$;

-- 상세: 자리 + 연대기 + 동네 평균 한 번에
create or replace function public.place_detail(p_key text)
returns jsonb
language sql stable as $$
  select jsonb_build_object(
    'place', to_jsonb(p),
    'history', coalesce((select jsonb_agg(to_jsonb(h) order by h.seq)
                         from public.place_history h where h.place_key = p.place_key), '[]'::jsonb),
    'dong', (select to_jsonb(r) from public.region_stats r
             where r.region_level = 'dong' and r.region_code = p.dong_code)
  )
  from public.places p where p.place_key = p_key;
$$;
