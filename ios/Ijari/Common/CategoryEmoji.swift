import Foundation

/// 업종 대분류 코드 → 이모지.
/// 매핑은 실데이터 `select distinct 상권업종대분류코드, 상권업종대분류명` 결과(서울 2026Q1, 10종) 기준.
enum CategoryEmoji {
    private static let map: [String: String] = [
        "G2": "🛍️",  // 소매
        "I1": "🛏️",  // 숙박
        "I2": "🍽️",  // 음식
        "L1": "🏠",  // 부동산
        "M1": "🔬",  // 과학·기술
        "N1": "🏢",  // 시설관리·임대
        "P1": "📚",  // 교육
        "Q1": "🏥",  // 보건의료
        "R1": "🎨",  // 예술·스포츠
        "S2": "🔧",  // 수리·개인
    ]

    /// 소분류 코드(예: "I21201")의 앞 2자리가 대분류 코드다. 매핑에 없으면 🏪
    static func emoji(categoryCode: String) -> String {
        map[String(categoryCode.prefix(2))] ?? "🏪"
    }
}
