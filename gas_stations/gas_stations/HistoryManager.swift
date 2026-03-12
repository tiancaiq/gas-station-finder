import Foundation

final class HistoryManager: ObservableObject {
    static let shared = HistoryManager()

    @Published private(set) var history: [VisitedStation] = []

    private let key = "fuel_advisor_history"

    private init() {
        load()
    }

    func addVisit(from station: StationResponse) {
        let item = VisitedStation(
            id: station.id,
            name: station.name,
            brand: station.brand,
            price: station.price,
            distanceMiles: station.distanceMiles,
            latitude: station.latitude,
            longitude: station.longitude,
            visitedAt: Date()
        )

        history.removeAll { $0.id == station.id }
        history.insert(item, at: 0)
        save()
    }

    func clear() {
        history.removeAll()
        save()
    }

    private func save() {
        do {
            let data = try JSONEncoder().encode(history)
            UserDefaults.standard.set(data, forKey: key)
        } catch {
            print("Failed to save history:", error.localizedDescription)
        }
    }

    private func load() {
        guard let data = UserDefaults.standard.data(forKey: key) else {
            history = []
            return
        }

        do {
            history = try JSONDecoder().decode([VisitedStation].self, from: data)
            history.sort { $0.visitedAt > $1.visitedAt }
        } catch {
            history = []
            print("Failed to load history:", error.localizedDescription)
        }
    }
}
