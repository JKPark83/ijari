import Foundation

/// region_stats 행 — map_regions RPC 응답
struct RegionStat: Codable, Identifiable, Hashable {
    let regionLevel: String
    let regionCode: String
    let regionName: String
    let centerLat: Double
    let centerLng: Double
    let placeCount: Int
    let turnoverSum: Int
    let turnoverAvg: Double
    let hotPlaceCount: Int
    let avgTenureMonths: Double?

    var id: String { "\(regionLevel)/\(regionCode)" }

    enum CodingKeys: String, CodingKey {
        case regionLevel = "region_level"
        case regionCode = "region_code"
        case regionName = "region_name"
        case centerLat = "center_lat"
        case centerLng = "center_lng"
        case placeCount = "place_count"
        case turnoverSum = "turnover_sum"
        case turnoverAvg = "turnover_avg"
        case hotPlaceCount = "hot_place_count"
        case avgTenureMonths = "avg_tenure_months"
    }
}
