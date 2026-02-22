import Foundation

// MARK: - Enums

enum Mode: String, CaseIterable, Identifiable {
    case emergency = "Emergency"
    case budget = "Budget"
    case comfort = "Comfort"
    var id: String { rawValue }

    var apiValue: String {
        switch self {
        case .emergency: return "emergency"
        case .budget: return "budget"
        case .comfort: return "comfort"
        }
    }
}

enum Priority: String, CaseIterable, Identifiable {
    case cheapest = "Cheapest"
    case closest = "Closest"
    case balanced = "Balanced"
    var id: String { rawValue }

    var apiValue: String {
        switch self {
        case .cheapest: return "cheapest"
        case .closest: return "closest"
        case .balanced: return "balanced"
        }
    }
}

// MARK: - Request JSON (iOS -> backend)

struct RecommendRequest: Codable {
    var mode: String

    // Emergency only
    var urgency: Double?

    // Budget only ($/gal)
    var budgetPriceCap: Double?

    // Comfort only
    var comfortIDontCare: Bool?

    var maxDistanceMiles: Int
    var priority: String
    var brand: String?
    var amenities: Amenities

    // Location
    var latitude: Double
    var longitude: Double
}

struct Amenities: Codable {
    var food: Bool
    var restroom: Bool
    var convenienceStore: Bool
}

// MARK: - Response JSON (backend -> iOS)
// Adjust these fields to match your backend response exactly.

struct StationResponse: Codable, Identifiable {
    let id: String
    let name: String
    let brand: String
    let price: Double
    let distanceMiles: Double
    let isOpen: Bool
    let why: String?
    let nearby: [String]?
    let latitude: Double
    let longitude: Double
}
