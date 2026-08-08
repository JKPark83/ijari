import SwiftUI

/// 자리 마커 — 교체 수 파랑 램프, 숫자 병기(색만으로 구분하지 않는다)
struct PlaceMarker: View {
    let place: Place

    var body: some View {
        Text("\(place.turnoverCount)")
            .font(.caption2.bold())
            .foregroundStyle(.white)
            .frame(width: 26, height: 26)
            .background(Circle().fill(rampColor))
            .overlay {
                // 공실 후보 → 테두리 점선 (MVP는 표시만, 필터 없음)
                if !place.isOccupied {
                    Circle().strokeBorder(style: StrokeStyle(lineWidth: 1.5, dash: [3, 2]))
                        .foregroundStyle(.white)
                }
            }
            // 층 미상(confidence low) → 덜 정확함의 시각 신호
            .opacity(place.isLowConfidence ? 0.5 : 1)
    }

    private var rampColor: Color {
        switch place.turnoverCount {
        case 0:  Color(hex: 0x9AA0A6)   // 회색 — 교체 이력 없음
        case 1:  Color(hex: 0x86B6EF)
        case 2:  Color(hex: 0x5598E7)
        case 3:  Color(hex: 0x2A78D6)
        case 4:  Color(hex: 0x1C5CAB)
        default: Color(hex: 0x104281)   // 5+
        }
    }
}
