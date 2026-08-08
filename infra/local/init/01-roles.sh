#!/bin/bash
# 첫 initdb 때만 실행 — PostgREST용 롤 구성 (Supabase 기본 롤 구조를 재현)
set -e

psql -v ON_ERROR_STOP=1 -U postgres -d ijari <<SQL
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
create role authenticator login password '${AUTHENTICATOR_PASSWORD}' noinherit;
grant anon to authenticator;
grant authenticated to authenticator;
grant service_role to authenticator;
grant usage on schema public to anon, authenticated, service_role;
SQL
