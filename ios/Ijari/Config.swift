import Foundation

enum Config {
    // 로컬 자가 호스팅 스택(맥 OrbStack: PostGIS+PostgREST, nginx :8000).
    // Tailscale IP(기기 고정)라 DHCP 영향이 없고, 폰의 Tailscale VPN만 켜져 있으면
    // 집 밖에서도 동작한다. LAN 직결로 되돌리려면 맥 IP(192.168.x.x)로 교체.
    // anon JWT는 공개해도 되는 키다 (RLS·grant가 읽기 전용을 강제). service_role과 혼동 금지.
    static let supabaseURL = URL(string: "http://100.82.214.33:8000")!
    static let supabaseAnonKey = "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJyb2xlIjogImFub24iLCAiaXNzIjogImlqYXJpLWxvY2FsIiwgImlhdCI6IDE3ODYxNTg4NTksICJleHAiOiAyMTAxNTE4ODU5fQ.T6xcx2x3S2TEmw942vmKD9b-uPmZSsy7jn5duBUn6jk"

    // 클라우드 Supabase(서울 데이터, 무료 티어)로 되돌릴 때 사용:
    // static let supabaseURL = URL(string: "https://refbsprzcfffuvzujpnp.supabase.co")!
    // static let supabaseAnonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJlZmJzcHJ6Y2ZmZnV2enVqcG5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxMjQ1NjUsImV4cCI6MjEwMTcwMDU2NX0.TOEsvN5gdlVOcDULfITXvA1Qu-CRRznfiRDOleCMQbc"
}
