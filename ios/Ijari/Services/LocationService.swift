import CoreLocation

/// 현재 위치 — 편의 기능일 뿐 앱의 전제가 아니다. 권한 없이 모든 기능이 동작해야 한다 (phase-4 문서 §5)
final class LocationService: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var status: CLAuthorizationStatus = .notDetermined
    @Published var lastLocation: CLLocationCoordinate2D?

    private let manager = CLLocationManager()

    override init() {
        super.init()
        manager.delegate = self
        status = manager.authorizationStatus
    }

    var isDenied: Bool {
        status == .denied || status == .restricted
    }

    /// 버튼 탭: 미결정 → 권한 요청, 승인됨 → 위치 한 번 조회. 거부 상태 처리는 UI 몫
    func requestOrLocate() {
        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse, .authorizedAlways:
            manager.requestLocation()
        default:
            break
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        DispatchQueue.main.async {
            self.status = manager.authorizationStatus
        }
        if manager.authorizationStatus == .authorizedWhenInUse
            || manager.authorizationStatus == .authorizedAlways {
            manager.requestLocation()
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let coordinate = locations.last?.coordinate else { return }
        DispatchQueue.main.async {
            self.lastLocation = coordinate
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // 위치 조회 실패는 무시 — 지도는 위치 없이도 완전하게 동작한다
    }
}
