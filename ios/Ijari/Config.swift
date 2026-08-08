import Foundation

enum Config {
    // anon key는 공개해도 되는 키다 (RLS가 읽기 전용을 강제). service_role과 혼동 금지.
    static let supabaseURL = URL(string: "https://refbsprzcfffuvzujpnp.supabase.co")!
    static let supabaseAnonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJlZmJzcHJ6Y2ZmZnV2enVqcG5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxMjQ1NjUsImV4cCI6MjEwMTcwMDU2NX0.TOEsvN5gdlVOcDULfITXvA1Qu-CRRznfiRDOleCMQbc"
}
