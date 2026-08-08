import Foundation
import Supabase

/// supabase-swift 래퍼 — RPC 3종 + bbox 반올림 키 메모리 캐시 (D4: 디스크 캐시 없음)
@MainActor
final class IjariClient {
    static let shared = IjariClient()

    private let client = SupabaseClient(supabaseURL: Config.supabaseURL,
                                        supabaseKey: Config.supabaseAnonKey)

    private var cache: [String: Any] = [:]
    private var cacheOrder: [String] = []
    private let cacheLimit = 50

    func mapPlaces(bbox: BBox, minTurnover: Int = 0, maxRows: Int = 500) async throws -> [Place] {
        let key = "places|\(bbox.roundedKey)|\(minTurnover)|\(maxRows)"
        if let hit = cached([Place].self, key) { return hit }

        struct Params: Encodable {
            let min_lng: Double, min_lat: Double, max_lng: Double, max_lat: Double
            let min_turnover: Int, max_rows: Int
        }
        let rows: [Place] = try await client
            .rpc("map_places", params: Params(min_lng: bbox.minLng, min_lat: bbox.minLat,
                                              max_lng: bbox.maxLng, max_lat: bbox.maxLat,
                                              min_turnover: minTurnover, max_rows: maxRows))
            .execute().value
        store(rows, key)
        return rows
    }

    func mapRegions(level: MapLevel, bbox: BBox) async throws -> [RegionStat] {
        guard let levelName = level.regionLevel else { return [] }
        let key = "regions|\(levelName)|\(bbox.roundedKey)"
        if let hit = cached([RegionStat].self, key) { return hit }

        struct Params: Encodable {
            let p_level: String
            let min_lng: Double, min_lat: Double, max_lng: Double, max_lat: Double
        }
        let rows: [RegionStat] = try await client
            .rpc("map_regions", params: Params(p_level: levelName,
                                               min_lng: bbox.minLng, min_lat: bbox.minLat,
                                               max_lng: bbox.maxLng, max_lat: bbox.maxLat))
            .execute().value
        store(rows, key)
        return rows
    }

    func placeDetail(key placeKey: String) async throws -> PlaceDetail {
        let key = "detail|\(placeKey)"
        if let hit = cached(PlaceDetail.self, key) { return hit }

        struct Params: Encodable { let p_key: String }
        let detail: PlaceDetail = try await client
            .rpc("place_detail", params: Params(p_key: placeKey))
            .execute().value
        store(detail, key)
        return detail
    }

    /// 앱 시작 시 한 번 — 데이터 기준 분기 표시용
    func appMeta() async throws -> AppMeta {
        let rows: [AppMetaRow] = try await client
            .from("app_meta").select("key, value")
            .execute().value
        return AppMeta(rows: rows)
    }

    // MARK: - 캐시

    private func cached<T>(_ type: T.Type, _ key: String) -> T? {
        cache[key] as? T
    }

    private func store(_ value: Any, _ key: String) {
        if cache[key] == nil { cacheOrder.append(key) }
        cache[key] = value
        while cacheOrder.count > cacheLimit {
            cache.removeValue(forKey: cacheOrder.removeFirst())
        }
    }
}
