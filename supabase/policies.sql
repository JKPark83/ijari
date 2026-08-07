-- 이 자리 — RLS (phase-2 문서 §3)
-- 앱은 anon key로 읽기만 한다. 쓰기는 service_role(ETL)만.

alter table public.places        enable row level security;
alter table public.place_history enable row level security;
alter table public.region_stats  enable row level security;
alter table public.app_meta      enable row level security;

create policy anon_read_places   on public.places        for select to anon, authenticated using (true);
create policy anon_read_history  on public.place_history for select to anon, authenticated using (true);
create policy anon_read_regions  on public.region_stats  for select to anon, authenticated using (true);
create policy anon_read_meta     on public.app_meta      for select to anon, authenticated using (true);

-- 이중 안전장치: 정책이 없어도 막히지만 권한 자체를 회수해 둔다
revoke insert, update, delete on all tables in schema public from anon, authenticated;
