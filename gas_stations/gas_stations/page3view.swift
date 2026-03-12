import SwiftUI

struct StationDetailView: View {
    let station: StationResponse

    @State private var showUpdateAlert = false
    @State private var priceInput = ""
    @State private var showThankYou = false
    @State private var showInvalidInput = false
    @State private var showUpdateFail = false
    @StateObject private var historyManager = HistoryManager.shared

    var body: some View {
        VStack(spacing: 16) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("\(station.brand) (Recommended)")
                        .font(.title3)
                        .fontWeight(.bold)
                    Spacer()
                }

                Divider()

                InfoRow(label: "Price:", value: String(format: "$%.2f", station.price))
                InfoRow(label: "Distance:", value: String(format: "%.1f miles", station.distanceMiles))
                InfoRow(label: "Open:", value: station.isOpen ? "Yes" : "No")

                if let nearby = station.nearby, !nearby.isEmpty {
                    InfoRow(label: "Nearby:", value: nearby.joined(separator: ", "))
                }
            }
            .padding(14)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(uiColor: .secondarySystemBackground))
            )
            .padding(.horizontal)

            Button {
                historyManager.addVisit(from: station)
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
                priceInput = ""
                showUpdateAlert = true
            } label: {
                Text("Update Price")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .buttonStyle(.bordered)
            .padding(.horizontal)

            Spacer()
        }
        .navigationTitle("Fuel Advisor")
        .navigationBarTitleDisplayMode(.inline)

        .alert("Update Price", isPresented: $showUpdateAlert) {
            TextField("Enter price (1-7)", text: $priceInput)
                .keyboardType(.decimalPad)

            Button("Submit") {
                sendPriceUpdate()
            }

            Button("Cancel", role: .cancel) { }
        } message: {
            Text("Enter a number between 1 and 7")
        }

        .alert("Thank you for updating!", isPresented: $showThankYou) {
            Button("OK") { }
        }
        .alert("Update failed", isPresented: $showUpdateFail){
            Button("OK"){ }
        }

        .alert("Invalid input", isPresented: $showInvalidInput) {
            Button("OK") { }
        } message: {
            Text("Please enter a valid number between 1 and 7.")
        }
    }

    private func sendPriceUpdate() {
        guard let price = Double(priceInput), price >= 1.0, price <= 7.0 else {
            showInvalidInput = true
            return
        }

        let payload = UpdatePriceRequest(
            stationId: station.id,
            newPrice: price
        )

        Task {
            do {
                try await APIClient.shared.updatePrice(payload: payload)
                showThankYou = true
            } catch {
                showUpdateFail = true
                print("Update failed: \(error.localizedDescription)")
            }
        }
    }
}

struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
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
