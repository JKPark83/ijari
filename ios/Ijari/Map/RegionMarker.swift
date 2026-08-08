import SwiftUI

/// 지역 마커 — 원형 배지: 큰 숫자 = 평균 교체 수, 작은 글씨 = 지역명. 탭하면 줌인만 한다
struct RegionMarker: View {
    let stat: RegionStat
    let onTap: () -> Void

    var body: some View {
        VStack(spacing: 1) {
            Text(String(format: "%.1f", stat.turnoverAvg))
                .font(.callout.bold())
            Text(stat.regionName)
                .font(.system(size: 9))
                .opacity(0.9)
                .lineLimit(1)
                .minimumScaleFactor(0.6)
        }
        .foregroundStyle(.white)
        .frame(width: 52, height: 52)
        .background(Circle().fill(Color(hex: 0x2A78D6)))
        .overlay(Circle().strokeBorder(.white.opacity(0.6), lineWidth: 1))
        .onTapGesture(perform: onTap)
    }
}
