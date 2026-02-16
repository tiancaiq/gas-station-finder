//
//  ContentView.swift
//  gas-UI
//
//  Created by B Shen on 2/14/26.
//

import SwiftUI
import MapKit

// MARK: - Models

enum Mode: String, CaseIterable, Identifiable {
    case emergency = "Emergency"
    case budget = "Budget"
    case comfort = "Comfort"
    var id: String { rawValue }
}

enum Priority: String, CaseIterable, Identifiable {
    case balanced = "Balanced"
    case cheapest = "Cheapest"
    case closest = "Closest"
    var id: String { rawValue }
}

struct Station: Identifiable {
    let id = UUID()
    let name: String
    let brand: String
    let price: Double
    let distanceMiles: Double
    let isOpen: Bool
    let amenities: [String]
    let coordinate: CLLocationCoordinate2D

    // Quick “explanation” placeholder
    var why: String {
        if !isOpen { return "Closed at arrival time" }
        return "Matches your mode & constraints"
    }
}

// MARK: - Demo Data

let demoStations: [Station] = [
    Station(name: "Arco - Campus", brand: "Arco", price: 4.99, distanceMiles: 2.1, isOpen: true,
            amenities: ["Food", "Convenience Store"],
            coordinate: CLLocationCoordinate2D(latitude: 33.6405, longitude: -117.8443)),
    Station(name: "Chevron - Main St", brand: "Chevron", price: 5.09, distanceMiles: 1.2, isOpen: true,
            amenities: ["Restroom"],
            coordinate: CLLocationCoordinate2D(latitude: 33.6500, longitude: -117.8400)),
    Station(name: "Shell - Plaza", brand: "Shell", price: 5.05, distanceMiles: 3.8, isOpen: true,
            amenities: ["Food"],
            coordinate: CLLocationCoordinate2D(latitude: 33.6300, longitude: -117.8600)),
    Station(name: "76 - Late Night", brand: "76", price: 4.89, distanceMiles: 6.5, isOpen: false,
            amenities: ["Convenience Store"],
            coordinate: CLLocationCoordinate2D(latitude: 33.6200, longitude: -117.8800))
]

// MARK: - Ranking (simple stub)

func rankStations(
    stations: [Station],
    mode: Mode,
    priority: Priority,
    urgency: Double,
    maxDistance: Double,
    preferredBrand: String?,
    desiredAmenities: Set<String>
) -> [Station] {
    // Filter
    var filtered = stations.filter { $0.distanceMiles <= maxDistance }
    if let brand = preferredBrand, brand != "Any" {
        filtered = filtered.filter { $0.brand == brand }
    }
    if !desiredAmenities.isEmpty {
        filtered = filtered.filter { !desiredAmenities.isDisjoint(with: Set($0.amenities)) }
    }

    // Basic scoring
    func score(_ s: Station) -> Double {
        if !s.isOpen { return -1_000 } // push closed down
        let priceScore = -s.price * 10
        let distScore = -s.distanceMiles * 5

        // urgency: higher urgency => favor distance more
        let urgencyWeight = 0.3 + (urgency * 0.7) // 0.3..1.0
        let costWeight = 1.0 - (urgency * 0.4)    // 1.0..0.6

        switch mode {
        case .emergency:
            return distScore * 2.0 + priceScore * 0.5
        case .budget:
            return priceScore * 2.0 + distScore * 0.5
        case .comfort:
            let amenityBonus = desiredAmenities.isEmpty ? 1.0 : 8.0
            return (distScore * urgencyWeight + priceScore * costWeight) + amenityBonus
        }
    }

    // Sort (priority nudges ordering)
    let sorted = filtered.sorted { a, b in
        let sa = score(a), sb = score(b)
        if priority == .closest { return a.distanceMiles < b.distanceMiles }
        if priority == .cheapest { return a.price < b.price }
        return sa > sb
    }

    return sorted
}

// MARK: - Views

struct ContentView: View {
    @State private var mode: Mode = .emergency
    @State private var priority: Priority = .balanced
    @State private var urgency: Double = 0.8
    @State private var maxDistance: Double = 6.0
    @State private var preferredBrand: String = "Any"
    @State private var wantFood = false
    @State private var wantRestroom = false
    @State private var wantStore = false

    @State private var goResults = false

    var desiredAmenities: Set<String> {
        var set: Set<String> = []
        if wantFood { set.insert("Food") }
        if wantRestroom { set.insert("Restroom") }
        if wantStore { set.insert("Convenience Store") }
        return set
    }

    var body: some View {
        NavigationStack {
            Form {
                Section(header: Text("Mode")) {
                    Picker("Mode", selection: $mode) {
                        ForEach(Mode.allCases) { m in
                            Text(m.rawValue).tag(m)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                Section(header: Text("Urgency & Limits")) {
                    HStack {
                        Text("Urgency")
                        Spacer()
                        Text(urgency >= 0.7 ? "High" : urgency >= 0.4 ? "Medium" : "Low")
                            .foregroundStyle(.secondary)
                    }
                    Slider(value: $urgency, in: 0...1)

                    HStack {
                        Text("Max distance")
                        Spacer()
                        Text("\(maxDistance, specifier: "%.0f") mi")
                            .foregroundStyle(.secondary)
                    }
                    Slider(value: $maxDistance, in: 1...15, step: 1)
                }

                Section(header: Text("Preference")) {
                    Picker("Priority", selection: $priority) {
                        ForEach(Priority.allCases) { p in
                            Text(p.rawValue).tag(p)
                        }
                    }

                    Picker("Brand", selection: $preferredBrand) {
                        Text("Any").tag("Any")
                        Text("Arco").tag("Arco")
                        Text("Chevron").tag("Chevron")
                        Text("Shell").tag("Shell")
                        Text("76").tag("76")
                    }
                }

                Section(header: Text("Amenities (optional)")) {
                    Toggle("Food", isOn: $wantFood)
                    Toggle("Restroom", isOn: $wantRestroom)
                    Toggle("Convenience store", isOn: $wantStore)
                }

                Section {
                    NavigationLink(
                        destination: ResultsView(
                            stations: demoStations,
                            mode: mode,
                            priority: priority,
                            urgency: urgency,
                            maxDistance: maxDistance,
                            preferredBrand: preferredBrand == "Any" ? nil : preferredBrand,
                            desiredAmenities: desiredAmenities
                        ),
                        isActive: $goResults
                    ) { EmptyView() }
                    Button("Show Recommendations") { goResults = true }
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            }
            .navigationTitle("Fuel Advisor")
        }
    }
}

struct ResultsView: View {
    let stations: [Station]
    let mode: Mode
    let priority: Priority
    let urgency: Double
    let maxDistance: Double
    let preferredBrand: String?
    let desiredAmenities: Set<String>

    var ranked: [Station] {
        rankStations(
            stations: stations,
            mode: mode,
            priority: priority,
            urgency: urgency,
            maxDistance: maxDistance,
            preferredBrand: preferredBrand,
            desiredAmenities: desiredAmenities
        )
    }

    var body: some View {
        List {
            if let first = ranked.first {
                Section(header: Text("Recommended")) {
                    NavigationLink(destination: StationDetailView(station: first)) {
                        StationRow(station: first, isRecommended: true)
                    }
                }
            }

            Section(header: Text("Other options")) {
                ForEach(ranked.dropFirst()) { s in
                    NavigationLink(destination: StationDetailView(station: s)) {
                        StationRow(station: s, isRecommended: false)
                    }
                }
            }
        }
        .navigationTitle("Results")
    }
}

struct StationRow: View {
    let station: Station
    let isRecommended: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(station.name).font(.headline)
                if isRecommended { Text("⭐").accessibilityLabel("Recommended") }
            }
            HStack(spacing: 10) {
                Text("\(station.distanceMiles, specifier: "%.1f") mi")
                Text("$\(station.price, specifier: "%.2f")")
                Text(station.isOpen ? "Open" : "Closed")
                    
            }
            Text("Why: \(station.why)")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 6)
    }
}

struct StationDetailView: View {
    let station: Station

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(station.name).font(.title2).bold()
            Text("Brand: \(station.brand)")
            Text("Price: $\(station.price, specifier: "%.2f")")
            Text("Distance: \(station.distanceMiles, specifier: "%.1f") mi")
            Text("Status: \(station.isOpen ? "Open" : "Closed")")
            Text("Nearby: \(station.amenities.joined(separator: ", "))")

            Spacer()

            Button("Open in Apple Maps") {
                openInMaps(coordinate: station.coordinate, name: station.name)
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
        .navigationTitle("Details")
    }

    private func openInMaps(coordinate: CLLocationCoordinate2D, name: String) {
        let placemark = MKPlacemark(coordinate: coordinate)
        let item = MKMapItem(placemark: placemark)
        item.name = name
        item.openInMaps(launchOptions: [MKLaunchOptionsDirectionsModeKey: MKLaunchOptionsDirectionsModeDriving])
    }
}

#Preview {
    ContentView()
}
