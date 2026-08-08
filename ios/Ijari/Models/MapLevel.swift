import MapKit

/// 줌 사다리 — 경도 폭(longitudeDelta) 기준 (plan-overview D2, 경계값은 잠정치)
enum MapLevel: Equatable {
    case sido, sigungu, dong, places

    init(span: MKCoordinateSpan) {
        switch span.longitudeDelta {
        case ..<0.08:  self = .places
        case ..<0.35:  self = .dong
        case ..<1.5:   self = .sigungu
        default:       self = .sido
        }
    }

    /// map_regions RPC의 p_level 값. places 레벨은 지역 마커가 아니므로 nil
    var regionLevel: String? {
        switch self {
        case .sido:    "sido"
        case .sigungu: "sigungu"
        case .dong:    "dong"
        case .places:  nil
        }
    }
}

/// RPC bbox 파라미터 묶음
struct BBox: Equatable {
    let minLng: Double
    let minLat: Double
    let maxLng: Double
    let maxLat: Double

    /// 메모리 캐시 키 — 소수 3자리(~110m)로 반올림해 근접 bbox를 같은 키로 묶는다
    var roundedKey: String {
        String(format: "%.3f,%.3f,%.3f,%.3f", minLng, minLat, maxLng, maxLat)
    }
}

extension MKCoordinateRegion {
    var bbox: BBox {
        BBox(minLng: center.longitude - span.longitudeDelta / 2,
             minLat: center.latitude - span.latitudeDelta / 2,
             maxLng: center.longitude + span.longitudeDelta / 2,
             maxLat: center.latitude + span.latitudeDelta / 2)
    }
}
