-- 로컬 스택 전용: 클라우드 Supabase가 기본 제공하는 롤 권한을 수동으로 부여한다.
-- schema.sql 적용 이후에 실행할 것 (초기화 스크립트는 테이블 생성 전이라 여기 분리).
grant usage on schema public to anon, authenticated, service_role;
grant select on all tables in schema public to anon, authenticated;
grant all on all tables in schema public to service_role;
grant execute on all functions in schema public to anon, authenticated, service_role;

-- 이후 새로 만드는 테이블·함수에도 같은 권한이 자동으로 붙게 한다
alter default privileges in schema public grant select on tables to anon, authenticated;
alter default privileges in schema public grant all on tables to service_role;
alter default privileges in schema public
  grant execute on functions to anon, authenticated, service_role;
