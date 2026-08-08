import Foundation

enum Config {
    // anon key는 공개해도 되는 키다 (RLS가 읽기 전용을 강제). service_role과 혼동 금지.
    static let supabaseURL = URL(string: "https://refbsprzcfffuvzujpnp.supabase.co")!
    // TODO: 대시보드 Settings → API Keys의 anon(publishable) 키로 교체
    static let supabaseAnonKey = "PASTE_SUPABASE_ANON_KEY"
}
