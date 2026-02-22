import SwiftUI

struct StationDetailView: View {
    let station: StationResponse

    var body: some View {
        VStack(spacing: 16) {
            // Info card
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("\(station.brand) (Recommended)")
                        .font(.title3)
                        .fontWeight(.bold)
                    Spacer()
                }

                Divider()

                infoRow(label: "Price:", value: String(format: "$%.2f", station.price))
                infoRow(label: "Distance:", value: String(format: "%.1f miles", station.distanceMiles))
                infoRow(label: "Open:", value: station.isOpen ? "Yes" : "No")

                if let nearby = station.nearby, !nearby.isEmpty {
                    infoRow(label: "Nearby:", value: nearby.joined(separator: ", "))
                }
            }
            .padding(14)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(uiColor: .secondarySystemBackground))
            )
            .padding(.horizontal)

            // Buttons
            Button {
                MapLauncher.openDirections(
                    latitude: station.latitude,
                    longitude: station.longitude,
                    name: station.name
                )
            } label: {
                Text("Open in Maps")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal)

            Button {
                // not implemented yet
            } label: {
                Text("Update Price")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .buttonStyle(.bordered)
            .padding(.horizontal)
            .disabled(true) // you said no need to implement now

            Spacer()
        }
        .navigationTitle("Fuel Advisor")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func infoRow(label: String, value: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .fontWeight(.semibold)
            Spacer()
            Text(value)
                .foregroundStyle(.secondary)
        }
    }
}

#Preview {
    NavigationStack {
        StationDetailView(
            station: StationResponse(
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
        )
    }
}
