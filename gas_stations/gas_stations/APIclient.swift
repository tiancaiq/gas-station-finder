import Foundation

final class APIClient {
    static let shared = APIClient()
    private init() {}

    // ✅ Simulator testing: "http://localhost:8000"
    // ✅ Real iPhone: "http://YOUR_COMPUTER_IP:8000"
    private let baseURL = URL(string: "http://192.168.1.27:8000")!

    enum APIError: Error, LocalizedError {
        case badHTTP(status: Int, body: String)

        var errorDescription: String? {
            switch self {
            case let .badHTTP(status, body):
                return "HTTP \(status): \(body)"
            }
        }
    }

    func recommend(payload: RecommendRequest) async throws -> [StationResponse] {
        let url = baseURL.appendingPathComponent("recommend")

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let encoder = JSONEncoder()
        req.httpBody = try encoder.encode(payload)

        let (data, resp) = try await URLSession.shared.data(for: req)

        guard let http = resp as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        guard (200...299).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.badHTTP(status: http.statusCode, body: body)
        }

        return try JSONDecoder().decode([StationResponse].self, from: data)
    }
}
