import Foundation

/// place_detail RPC 응답 — 자리 + 연대기 + 동네 평균 한 번에 (Phase 4에서 사용)
struct PlaceDetail: Codable {
    let place: Place
    let history: [HistoryEntry]
    let dong: RegionStat?
}

/// place_history 행 — 논리적 점포(ID 재발급 병합 후) 하나
struct HistoryEntry: Codable, Identifiable, Hashable {
    let placeKey: String
    let seq: Int
    let startQuarter: String
    let endQuarter: String?          // nil = 마지막 분기에도 영업 중
    let categoryCode: String
    let categoryName: String
    let tenureQuarters: Int?

    var id: Int { seq }

    enum CodingKeys: String, CodingKey {
        case placeKey = "place_key"
        case seq
        case startQuarter = "start_quarter"
        case endQuarter = "end_quarter"
        case categoryCode = "category_code"
        case categoryName = "category_name"
        case tenureQuarters = "tenure_quarters"
    }
}
