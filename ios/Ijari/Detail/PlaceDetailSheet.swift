import SwiftUI

/// 자리 연대기 상세 — 헤드라인·타임라인·동네 비교·데이터 기준의 4단 구성 (phase-4 문서)
struct PlaceDetailSheet: View {
    let placeKey: String
    let meta: AppMeta?

    @State private var detail: PlaceDetail?
    @State private var loadState: LoadState = .idle

    private let client = IjariClient.shared

    var body: some View {
        Group {
            if let detail {
                content(detail)
            } else if loadState.isFailed {
                failedView
            } else {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .task(id: placeKey) { await load() }
    }

    private func load() async {
        loadState = .loading
        do {
            detail = try await client.placeDetail(key: placeKey)
            loadState = .loaded
        } catch is CancellationError {
        } catch {
            loadState = .failed(error)
        }
    }

    private var failedView: some View {
        VStack(spacing: 12) {
            Text("정보를 불러오지 못했습니다")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Button("다시 시도") {
                Task { await load() }
            }
            .buttonStyle(.bordered)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - 본문

    private func content(_ detail: PlaceDetail) -> some View {
        let (headline, subline) = headlineText(detail)
        return ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(headline)
                        .font(.title3.bold())
                    if let subline {
                        Text(subline)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }

                if detail.place.isLowConfidence {
                    Text("층 정보 없음 — 건물 단위 추정")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(.yellow.opacity(0.25)))
                }

                Text(addressLine(detail.place))
                    .font(.footnote)
                    .foregroundStyle(.secondary)

                Divider()

                timeline(detail.history)

                if let dongLine = dongComparison(detail) {
                    Divider()
                    Text(dongLine)
                        .font(.subheadline)
                }

                if let meta {
                    Text(meta.footerText)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .padding(.top, 8)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(20)
        }
    }

    /// "서울특별시 강남구 ○○로 12 · 1층 · 평균 9개월"
    private func addressLine(_ place: Place) -> String {
        var parts = [place.roadAddress]
        parts.append(place.floorLabel == "미상" ? "층 미상" : "\(place.floorLabel)층")
        // 종료된 점유가 없으면 avg_tenure_months가 null — 0으로 표시하지 않는다
        if let avg = place.avgTenureMonths {
            parts.append("평균 \(Int(avg.rounded()))개월")
        }
        return parts.joined(separator: " · ")
    }

    // MARK: - 헤드라인 — 케이스가 전부다 (단정 표현 금지)

    private func headlineText(_ detail: PlaceDetail) -> (String, String?) {
        let place = detail.place

        if !place.isOccupied {
            let lastEnd = detail.history.compactMap(\.endQuarter).max()
            return ("지금은 비어 있는 것으로 보이는 자리",
                    lastEnd.map { "마지막 영업 기록: \(QuarterFormat.korean($0))" })
        }
        if place.storesCurrent >= 2 {
            return ("이 층 점포 \(place.storesCurrent)곳 · 교체 \(place.turnoverCount)번",
                    "층 단위 정보라 점포별 구분은 정확하지 않을 수 있어요")
        }
        if place.turnoverCount >= 1 {
            let subline = place.avgTenureMonths.map {
                "평균 \(Int($0.rounded()))개월마다 새 가게가 들어왔어요"
            }
            return ("이 자리, 주인이 \(place.turnoverCount)번 바뀌었습니다", subline)
        }
        if place.firstQuarter == "2023Q1" {
            return ("한 가게가 3년 넘게 지키고 있는 자리", "2023년 1분기부터 계속 영업 중")
        }
        return ("한 가게가 지키고 있는 자리",
                "\(QuarterFormat.koreanLong(place.firstQuarter))부터 계속 영업 중")
    }

    // MARK: - 타임라인 — 업종명 + 기간뿐 (상호명은 스키마에 없다)

    private func timeline(_ history: [HistoryEntry]) -> some View {
        let entries = history.sorted { $0.seq > $1.seq }   // 최신이 위
        return VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(entries.enumerated()), id: \.element.id) { index, entry in
                timelineRow(entry, isLast: index == entries.count - 1)
            }
        }
    }

    private func timelineRow(_ entry: HistoryEntry, isLast: Bool) -> some View {
        let isCurrent = entry.endQuarter == nil
        return HStack(alignment: .top, spacing: 10) {
            VStack(spacing: 0) {
                Circle()
                    .fill(isCurrent ? Color.accentColor : Color.secondary.opacity(0.5))
                    .frame(width: 8, height: 8)
                    .padding(.top, 5)
                if !isLast {
                    Rectangle()
                        .fill(Color.secondary.opacity(0.25))
                        .frame(width: 1)
                }
            }
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Text("\(CategoryEmoji.emoji(categoryCode: entry.categoryCode)) \(entry.categoryName)")
                        .font(.subheadline.weight(.semibold))
                    if isCurrent {
                        Text("영업 중")
                            .font(.caption2.bold())
                            .foregroundStyle(Color.accentColor)
                    }
                }
                Text(periodText(entry))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.bottom, isLast ? 0 : 14)
        }
    }

    /// "2024.2분기 ~ 2025.2분기 (1년)" / "2025.3분기 ~ 영업 중"
    private func periodText(_ entry: HistoryEntry) -> String {
        let start = QuarterFormat.korean(entry.startQuarter)
        guard let end = entry.endQuarter else { return "\(start) ~ 영업 중" }
        var text = "\(start) ~ \(QuarterFormat.korean(end))"
        if let tenure = QuarterFormat.tenureText(quarters: entry.tenureQuarters) {
            text += " (\(tenure))"
        }
        return text
    }

    // MARK: - 동네 비교 한 줄

    private func dongComparison(_ detail: PlaceDetail) -> String? {
        guard let dong = detail.dong, dong.turnoverAvg > 0 else { return nil }
        let avg = String(format: "%.1f", dong.turnoverAvg)
        let ratio = Double(detail.place.turnoverCount) / dong.turnoverAvg
        if ratio >= 2 { return "이 동네 평균(\(avg)번)보다 눈에 띄게 잦은 자리예요" }
        if ratio > 0.5 { return "이 동네 평균(\(avg)번)과 비슷한 수준이에요" }
        return "이 동네 평균(\(avg)번)보다 오래 버티는 자리예요"
    }
}
