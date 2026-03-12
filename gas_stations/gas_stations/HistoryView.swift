import SwiftUI

struct HistoryView: View {
    @StateObject private var historyManager = HistoryManager.shared

    var body: some View {
        List {
            if historyManager.history.isEmpty {
                ContentUnavailableView(
                    "No history yet",
                    systemImage: "clock.arrow.circlepath",
                    description: Text("Stations you open in Maps will appear here.")
                )
            } else {
                ForEach(historyManager.history) { station in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(station.brand)
                            .font(.headline)

                        Text(station.name)
                            .foregroundStyle(.secondary)

                        Text(String(format: "$%.2f • %.1f mi", station.price, station.distanceMiles))
                            .font(.subheadline)

                        Text("Visited \(formatted(station.visitedAt))")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .navigationTitle("History")
        .toolbar {
            if !historyManager.history.isEmpty {
                Button("Clear") {
                    historyManager.clear()
                }
            }
        }
    }

    private func formatted(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

#Preview {
    NavigationStack {
        HistoryView()
    }
}
