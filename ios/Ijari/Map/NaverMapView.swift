import SwiftUI
import NMapsMap

/// 카메라 이동 명령 — id가 바뀔 때만 지도에 적용한다 (SwiftUI 상태 → 지도 단방향)
struct CameraCommand: Equatable {
    let id = UUID()
    let centerLat: Double
    let centerLng: Double
    /// 화면에 보일 경도 폭 — MapLevel 사다리와 같은 단위
    let lngDelta: Double
    var animated = true
}

/// NMFMapView 래퍼 — 마커 동기화 + 카메라 유휴 콜백 + 이동 명령 적용
struct NaverMapView: UIViewRepresentable {
    let markers: MapScreen.Markers
    let camera: CameraCommand
    let onCameraIdle: (BBox, Double) -> Void
    let onPlaceTap: (Place) -> Void
    let onRegionTap: (RegionStat) -> Void

    func makeUIView(context: Context) -> NMFMapView {
        let map = NMFMapView(frame: .zero)
        map.addCameraDelegate(delegate: context.coordinator)
        context.coordinator.apply(camera, to: map)
        return map
    }

    func updateUIView(_ map: NMFMapView, context: Context) {
        context.coordinator.parent = self
        if camera.id != context.coordinator.appliedCameraId {
            context.coordinator.apply(camera, to: map)
        }
        context.coordinator.sync(markers: markers, on: map)
    }

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    final class Coordinator: NSObject, NMFMapViewCameraDelegate {
        var parent: NaverMapView
        var appliedCameraId: UUID?
        private var overlays: [NMFMarker] = []
        private var lastMarkers: MapScreen.Markers?
        /// 자리 아이콘은 (교체 수·공실·신뢰도) 조합이 유한해 렌더링 결과를 재사용한다
        private var placeIconCache: [String: NMFOverlayImage] = [:]

        init(parent: NaverMapView) { self.parent = parent }

        func apply(_ camera: CameraCommand, to map: NMFMapView) {
            appliedCameraId = camera.id
            // 경도 폭 → 줌 레벨 (웹 메르카토르: 줌 0에서 세계 360°가 256pt)
            let width = map.frame.width > 0 ? map.frame.width : 390
            let zoom = log2(360 * width / (256 * camera.lngDelta))
            let update = NMFCameraUpdate(scrollTo: NMGLatLng(lat: camera.centerLat, lng: camera.centerLng),
                                         zoomTo: zoom)
            if camera.animated { update.animation = .easeOut }
            map.moveCamera(update)
        }

        func mapViewCameraIdle(_ mapView: NMFMapView) {
            guard mapView.frame.width > 0 else { return }   // 레이아웃 전 이벤트 무시
            let bounds = mapView.contentBounds
            let bbox = BBox(minLng: bounds.southWest.lng, minLat: bounds.southWest.lat,
                            maxLng: bounds.northEast.lng, maxLat: bounds.northEast.lat)
            parent.onCameraIdle(bbox, bounds.northEast.lng - bounds.southWest.lng)
        }

        @MainActor
        func sync(markers: MapScreen.Markers, on map: NMFMapView) {
            guard markers != lastMarkers else { return }
            lastMarkers = markers
            overlays.forEach { $0.mapView = nil }
            overlays.removeAll()

            switch markers {
            case .places(let places):
                for place in places {
                    let marker = NMFMarker(position: NMGLatLng(lat: place.lat, lng: place.lng))
                    marker.iconImage = placeIcon(for: place)
                    marker.width = 26
                    marker.height = 26
                    marker.anchor = CGPoint(x: 0.5, y: 0.5)
                    marker.touchHandler = { [weak self] _ in
                        self?.parent.onPlaceTap(place)
                        return true
                    }
                    marker.mapView = map
                    overlays.append(marker)
                }
            case .regions(let regions):
                for stat in regions {
                    let marker = NMFMarker(position: NMGLatLng(lat: stat.centerLat, lng: stat.centerLng))
                    marker.iconImage = NMFOverlayImage(image: Self.render(RegionMarker(stat: stat, onTap: {}), size: 52))
                    marker.width = 52
                    marker.height = 52
                    marker.anchor = CGPoint(x: 0.5, y: 0.5)
                    marker.touchHandler = { [weak self] _ in
                        self?.parent.onRegionTap(stat)
                        return true
                    }
                    marker.mapView = map
                    overlays.append(marker)
                }
            }
        }

        @MainActor
        private func placeIcon(for place: Place) -> NMFOverlayImage {
            let key = "\(place.turnoverCount)|\(place.isOccupied)|\(place.isLowConfidence)"
            if let hit = placeIconCache[key] { return hit }
            let image = NMFOverlayImage(image: Self.render(PlaceMarker(place: place), size: 26))
            placeIconCache[key] = image
            return image
        }

        /// SwiftUI 마커 뷰를 그대로 이미지로 굽는다 — 디자인 코드 재사용
        @MainActor
        private static func render<V: View>(_ view: V, size: CGFloat) -> UIImage {
            let renderer = ImageRenderer(content: view.frame(width: size, height: size))
            renderer.scale = UIScreen.main.scale
            return renderer.uiImage ?? UIImage()
        }
    }
}
