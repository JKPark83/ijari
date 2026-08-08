import Foundation

enum LoadState {
    case idle
    case loading
    case loaded
    case failed(Error)

    var isFailed: Bool {
        if case .failed = self { return true }
        return false
    }
}
