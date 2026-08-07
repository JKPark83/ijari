-- 이 자리 — DDL (phase-2 문서 §2)
-- Supabase SQL Editor에서 실행. 재실행 시에는 drop 후 실행한다.

create extension if not exists postgis;

-- 자리: 건물관리번호 + 층. 지도에 찍히는 단위
create table public.places (
  place_key         text primary key,          -- building_id#floor_label
  building_id       text not null,
  floor_label       text not null,             -- '1' / '2' / '미상'
  road_address      text not null,
  sido_code         text not null,
  sigungu_code      text not null,
  dong_code         text not null,             -- 행정동 코드: dong 집계 연결키
  lat               double precision not null,
  lng               double precision not null,
  geom              geometry(point, 4326)
                    generated always as (st_setsrid(st_makepoint(lng, lat), 4326)) stored,
  turnover_count    smallint not null default 0,
  avg_tenure_months real,                      -- 종료된 점유만 평균. 없으면 null
  confidence        text not null default 'high' check (confidence in ('high','low')),
  stores_current    smallint not null default 0,  -- 현재 분기 점포 수. 0 = 공실 후보
  is_occupied       boolean not null default true,
  current_category_code text,
  current_category_name text,
  first_quarter     text not null,             -- '2023Q1'
  last_quarter      text not null
);
create index places_geom_idx     on public.places using gist (geom);
create index places_turnover_idx on public.places (turnover_count desc);
create index places_dong_idx     on public.places (dong_code);

-- 자리 연대기: 논리적 점포(ID 재발급 병합 후) 하나가 한 행
create table public.place_history (
  place_key       text not null references public.places on delete cascade,
  seq             smallint not null,           -- 자리 안 순번 (start_quarter 오름차순)
  start_quarter   text not null,
  end_quarter     text,                        -- null = 마지막 분기에도 영업 중
  category_code   text not null,
  category_name   text not null,               -- 상호명 컬럼은 의도적으로 없다
  tenure_quarters smallint,
  primary key (place_key, seq)
);

-- 사전 집계: 줌아웃 지도용 (D2)
create table public.region_stats (
  region_level      text not null check (region_level in ('sido','sigungu','dong')),
  region_code       text not null,
  region_name       text not null,
  center_lat        double precision not null, -- 소속 자리 좌표 평균
  center_lng        double precision not null,
  place_count       integer not null,
  turnover_sum      integer not null,
  turnover_avg      real not null,
  hot_place_count   integer not null,          -- 교체 3회 이상 자리 수
  avg_tenure_months real,
  primary key (region_level, region_code)
);
create index region_stats_center_idx on public.region_stats (region_level, center_lat, center_lng);

create table public.app_meta (
  key        text primary key,                 -- latest_quarter / coverage / data_version
  value      text not null,
  updated_at timestamptz not null default now()
);
