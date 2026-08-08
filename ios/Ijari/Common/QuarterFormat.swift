import Foundation

/// 분기 문자열("2023Q1") 표기 변환
enum QuarterFormat {
    /// "2023Q1" → "2023.1분기"
    static func korean(_ quarter: String) -> String {
        let parts = quarter.split(separator: "Q")
        guard parts.count == 2 else { return quarter }
        return "\(parts[0]).\(parts[1])분기"
    }

    /// "2023Q1" → "2023년 1분기"
    static func koreanLong(_ quarter: String) -> String {
        let parts = quarter.split(separator: "Q")
        guard parts.count == 2 else { return quarter }
        return "\(parts[0])년 \(parts[1])분기"
    }

    /// 점유 분기 수 → "1년 3개월" (분기 해상도 설명은 하단 데이터 기준 문구가 담당 — "약"을 붙이지 않는다)
    static func tenureText(quarters: Int?) -> String? {
        guard let quarters, quarters > 0 else { return nil }
        let months = quarters * 3
        let years = months / 12
        let rest = months % 12
        if years == 0 { return "\(months)개월" }
        if rest == 0 { return "\(years)년" }
        return "\(years)년 \(rest)개월"
    }
}
