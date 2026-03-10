import Foundation

@MainActor
final class FuelAdvisorVM: ObservableObject {
    // UI state
    @Published var mode: Mode = .emergency

    @Published var urgency: Double = 0.40              // 0...1
    @Published var budgetPriceCap: Double = 5.00       // 1...7
    @Published var comfortIDontCare: Bool = true

    @Published var maxDistanceMiles: Int = 6
    @Published var priority: Priority = .cheapest
    @Published var brandText: String = ""

    @Published var food: Bool = false
    @Published var restroom: Bool = false
    @Published var convenienceStore: Bool = false

    // Location
    @Published var latitude: Double? = nil
    @Published var longitude: Double? = nil

    // Networking state
    @Published var isLoading: Bool = false
    @Published var errorMessage: String? = nil
    @Published var stations: [StationResponse] = []
    @Published var showResults: Bool = false
    // Debug JSON preview
    @Published var requestJSONPreview: String = ""

    func onModeChanged(_ newMode: Mode) {
        switch newMode {
        case .emergency:
            priority = .closest
        case .budget:
            priority = .cheapest
        case .comfort:
            priority = .balanced
            comfortIDontCare = true
        }
        updatePreviewJSON()
    }

    func buildRequest() throws -> RecommendRequest {
        guard let lat = latitude, let lon = longitude else {
            throw NSError(domain: "Location", code: 0, userInfo: [NSLocalizedDescriptionKey: "Location not ready yet."])
        }

        let trimmedBrand = brandText.trimmingCharacters(in: .whitespacesAndNewlines)

        return RecommendRequest(
            mode: mode.apiValue,
            urgency: mode == .emergency ? urgency : nil,
            budgetPriceCap: mode == .budget ? budgetPriceCap : nil,
            comfortIDontCare: mode == .comfort ? comfortIDontCare : nil,
            maxDistanceMiles: maxDistanceMiles,
            priority: priority.apiValue,
            brand: trimmedBrand.isEmpty ? nil : trimmedBrand,
            amenities: Amenities(food: food, restroom: restroom, convenienceStore: convenienceStore),
            latitude: lat,
            longitude: lon
        )
    }

    func updatePreviewJSON() {
        do {
            let req = try buildRequest()
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let data = try encoder.encode(req)
            requestJSONPreview = String(data: data, encoding: .utf8) ?? ""
        } catch {
            requestJSONPreview = "JSON not ready: \(error.localizedDescription)"
        }
    }

    func requestStations() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let payload = try buildRequest()
            // keep preview updated
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            requestJSONPreview = String(data: try encoder.encode(payload), encoding: .utf8) ?? ""
            
            stations = try await APIClient.shared.recommend(payload: payload)
            showResults = true
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
