import SwiftUI

struct RecommendationsView: View {
    let stations: [StationResponse]

    var body: some View {
        List {
            Section {
                Text("Recommended for you")
                    .font(.title2)
                    .fontWeight(.bold)
                    .listRowInsets(EdgeInsets())
                    .padding(.vertical, 6)
            }

            ForEach(Array(stations.enumerated()), id: \.element.id) { idx, s in
                NavigationLink {
                    StationDetailView(station: s)
                } label: {
                    StationRow(rank: idx + 1, station: s)
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Fuel Advisor")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct StationRow: View {
    let rank: Int
    let station: StationResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                if rank == 1 {
                    Image(systemName: "star.fill")
                        .foregroundStyle(.yellow)
                } else {
                    Text("\(rank).")
                        .foregroundStyle(.secondary)
                        .fontWeight(.semibold)
                }

                Text("\(station.brand)")
                    .font(.headline)

                Spacer()

                Text(String(format: "%.1f mi", station.distanceMiles))
                    .foregroundStyle(.secondary)

                Text(String(format: "$%.2f", station.price))
                    .fontWeight(.semibold)

                Text(station.isOpen ? "Open" : "Closed")
                    .foregroundColor(station.isOpen ? .secondary : .red)
            }

            if let why = station.why, !why.isEmpty {
                Text("Why: \(why)")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 6)
    }
}
#Preview {
    NavigationStack {
        RecommendationsView(
            stations: [
                StationResponse(
                    id: "1",
                    name: "ARCO",
                    brand: "ARCO",
                    price: 4.99,
                    distanceMiles: 2.1,
                    isOpen: true,
                    why: "Cheapest within 6 mi",
                    nearby: ["McDonald's", "7-Eleven"],
                    latitude: 33.6405,
                    longitude: -117.8443
                )
            ]
        )
    }
}
