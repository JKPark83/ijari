import SwiftUI
import MapKit

/// 지도 골격 — 레벨 전환 + 0.3s 디바운스 + 직전 요청 취소 (phase-3 문서 §4)
/// + 상세 바텀시트·현재 위치·데이터 기준 상시 표시 (phase-4)
struct MapScreen: View {
    /// 서울 전체 뷰 (Δ0.45 → sigungu 레벨에서 시작)
    private static let seoulRegion = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.5519, longitude: 126.9918),
        span: MKCoordinateSpan(latitudeDelta: 0.45, longitudeDelta: 0.45))

    enum Markers {
        case regions([RegionStat])
        case places([Place])

        var isEmpty: Bool {
            switch self {
            case .regions(let r): r.isEmpty
            case .places(let p): p.isEmpty
            }
        }
    }

    struct SelectedPlace: Identifiable {
        let key: String
        var id: String { key }
    }

    @State private var position: MapCameraPosition = .region(Self.seoulRegion)
    @State private var markers: Markers = .regions([])
    @State private var loadState: LoadState = .idle
    @State private var loadTask: Task<Void, Never>?
    @State private var lastRegion: MKCoordinateRegion?
    @State private var retriedOnce = false

    @State private var selectedPlace: SelectedPlace?
    @State private var meta: AppMeta?
    @State private var showLocationDeniedAlert = false
    @StateObject private var location = LocationService()

    private let client = IjariClient.shared

    var body: some View {
        ZStack(alignment: .top) {
            map
            if loadState.isFailed && !markers.isEmpty {
                errorBanner
            }
        }
        .overlay(alignment: .bottomTrailing) { locationButton }
        .overlay(alignment: .bottom) { dataFooter }
        .overlay {
            if loadState.isFailed && markers.isEmpty {
                offlineNotice
            }
        }
        .sheet(item: $selectedPlace) { selected in
            PlaceDetailSheet(placeKey: selected.key, meta: meta)
                .presentationDetents([.medium, .large])
                .presentationBackgroundInteraction(.enabled(upThrough: .medium))  // 지도 계속 조작 가능
        }
        .task {
            meta = try? await client.appMeta()
        }
        .onReceive(location.$lastLocation) { coordinate in
            guard let coordinate else { return }
            withAnimation {
                position = .region(MKCoordinateRegion(
                    center: coordinate,
                    span: MKCoordinateSpan(latitudeDelta: 0.03, longitudeDelta: 0.03)))  // places 레벨
            }
        }
        .alert("위치 권한이 꺼져 있습니다", isPresented: $showLocationDeniedAlert) {
            Button("설정 열기") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            Button("닫기", role: .cancel) {}
        } message: {
            Text("설정 앱에서 위치 접근을 허용하면 내 주변의 자리를 볼 수 있습니다.")
        }
    }

    private var map: some View {
        Map(position: $position) {
            switch markers {
            case .places(let places):
                ForEach(places) { place in
                    Annotation("", coordinate: CLLocationCoordinate2D(latitude: place.lat,
                                                                      longitude: place.lng)) {
                        PlaceMarker(place: place)
                            .onTapGesture { selectedPlace = SelectedPlace(key: place.placeKey) }
                    }
                }
            case .regions(let regions):
                ForEach(regions) { region in
                    Annotation("", coordinate: CLLocationCoordinate2D(latitude: region.centerLat,
                                                                      longitude: region.centerLng)) {
                        RegionMarker(stat: region) { zoomIn(to: region) }
                    }
                }
            }
        }
        .onMapCameraChange(frequency: .continuous) { context in
            onCameraChange(context)
        }
    }

    // MARK: - 로딩

    private func onCameraChange(_ context: MapCameraUpdateContext) {
        lastRegion = context.region
        loadTask?.cancel()                       // 이전 요청 취소
        loadTask = Task {
            try? await Task.sleep(for: .seconds(0.3))   // 디바운스
            guard !Task.isCancelled else { return }
            await load(region: context.region)
        }
    }

    private func load(region: MKCoordinateRegion) async {
        let level = MapLevel(span: region.span)
        loadState = .loading
        do {
            switch level {
            case .places:
                markers = .places(try await client.mapPlaces(bbox: region.bbox))
            default:
                markers = .regions(try await client.mapRegions(level: level, bbox: region.bbox))
            }
            loadState = .loaded
            retriedOnce = false
        } catch is CancellationError {
        } catch {
            guard !Task.isCancelled else { return }
            loadState = .failed(error)
            // 조작 중 일시 실패 → 기존 마커 유지 + 자동 재시도 1회
            if !markers.isEmpty && !retriedOnce {
                retriedOnce = true
                try? await Task.sleep(for: .seconds(2))
                guard !Task.isCancelled else { return }
                await load(region: region)
            }
        }
    }

    private func retry() {
        retriedOnce = false
        let region = lastRegion ?? Self.seoulRegion
        loadTask?.cancel()
        loadTask = Task { await load(region: region) }
    }

    private func zoomIn(to stat: RegionStat) {
        let nextDelta: Double = switch stat.regionLevel {
        case "sido":    0.5     // → sigungu
        case "sigungu": 0.15    // → dong
        default:        0.05    // → places
        }
        withAnimation {
            position = .region(MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: stat.centerLat, longitude: stat.centerLng),
                span: MKCoordinateSpan(latitudeDelta: nextDelta, longitudeDelta: nextDelta)))
        }
    }

    // MARK: - 현재 위치 (권한 없이도 모든 기능이 동작해야 한다)

    private var locationButton: some View {
        Button {
            if location.isDenied {
                showLocationDeniedAlert = true
            } else {
                location.requestOrLocate()
            }
        } label: {
            Image(systemName: location.isDenied ? "location.slash" : "location.fill")
                .font(.system(size: 18))
                .frame(width: 44, height: 44)
                .background(.thinMaterial, in: Circle())
        }
        .opacity(location.isDenied ? 0.5 : 1)
        .padding(.trailing, 14)
        .padding(.bottom, 44)
    }

    // MARK: - 데이터 기준 상시 표시

    @ViewBuilder
    private var dataFooter: some View {
        if let meta {
            Text(meta.footerText)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(.thinMaterial, in: Capsule())
                .padding(.bottom, 6)
        }
    }

    // MARK: - 오프라인·에러 UX (D4 온라인 전용의 대가)

    private var offlineNotice: some View {
        VStack(spacing: 16) {
            Image(systemName: "wifi.slash")
                .font(.system(size: 44))
                .foregroundStyle(.secondary)
            Text("인터넷 연결이 필요한 앱입니다")
                .font(.headline)
            Button("다시 시도", action: retry)
                .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.background)
    }

    private var errorBanner: some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.caption)
            Text("일시적인 오류가 발생했습니다")
                .font(.caption)
            Spacer()
            Button("다시 시도", action: retry)
                .font(.caption.bold())
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .padding(.horizontal, 12)
        .padding(.top, 4)
    }
}

#Preview {
    MapScreen()
}
