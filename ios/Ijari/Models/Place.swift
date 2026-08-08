import Foundation

/// places 행 — map_places RPC 응답. geom(GeoJSON)은 앱에서 쓰지 않아 디코딩하지 않는다.
struct Place: Codable, Identifiable, Hashable {
    let placeKey: String
    let buildingId: String
    let floorLabel: String
    let roadAddress: String
    let sidoCode: String
    let sigunguCode: String
    let dongCode: String
    let lat: Double
    let lng: Double
    let turnoverCount: Int
    let avgTenureMonths: Double?
    let confidence: String
    let storesCurrent: Int
    let isOccupied: Bool
    let currentCategoryCode: String?
    let currentCategoryName: String?
    let firstQuarter: String
    let lastQuarter: String

    var id: String { placeKey }
    var isLowConfidence: Bool { confidence == "low" }

    enum CodingKeys: String, CodingKey {
        case placeKey = "place_key"
        case buildingId = "building_id"
        case floorLabel = "floor_label"
        case roadAddress = "road_address"
        case sidoCode = "sido_code"
        case sigunguCode = "sigungu_code"
        case dongCode = "dong_code"
        case lat, lng
        case turnoverCount = "turnover_count"
        case avgTenureMonths = "avg_tenure_months"
        case confidence
        case storesCurrent = "stores_current"
        case isOccupied = "is_occupied"
        case currentCategoryCode = "current_category_code"
        case currentCategoryName = "current_category_name"
        case firstQuarter = "first_quarter"
        case lastQuarter = "last_quarter"
    }
}
