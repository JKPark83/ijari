import Foundation

/// app_meta 행 (key-value)
struct AppMetaRow: Codable {
    let key: String
    let value: String
}

/// 앱 시작 시 한 번 읽어 메모리에 두는 데이터 기준 정보
struct AppMeta {
    let latestQuarter: String?   // "2026Q1"
    let coverage: String?        // "서울"

    init(rows: [AppMetaRow]) {
        let dict = Dictionary(uniqueKeysWithValues: rows.map { ($0.key, $0.value) })
        latestQuarter = dict["latest_quarter"]
        coverage = dict["coverage"]
    }

    /// "2026년 1분기 데이터 기준 · 서울 · 소상공인시장진흥공단 상가(상권)정보"
    var footerText: String {
        var parts: [String] = []
        if let latestQuarter {
            parts.append("\(QuarterFormat.koreanLong(latestQuarter)) 데이터 기준")
        }
        if let coverage { parts.append(coverage) }
        parts.append("소상공인시장진흥공단 상가(상권)정보")
        return parts.joined(separator: " · ")
    }
}
