import SwiftUI

struct ContentView: View {
    @StateObject private var vm = FuelAdvisorVM()
    @StateObject private var locationManager = LocationManager()
//    @State private var showResults = false
    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {

                // Mode segmented
                Picker("", selection: $vm.mode) {
                    ForEach(Mode.allCases) { m in
                        Text(m.rawValue).tag(m)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.top, 8)
                .onChange(of: vm.mode) { _, newMode in
                    vm.onModeChanged(newMode)
                }

                ScrollView {
                    VStack(spacing: 12) {

                        // Mode-specific card
                        Card {
                            VStack(alignment: .leading, spacing: 10) {

                                if vm.mode == .emergency {
                                    Text("Urgency").font(.headline)
                                    Slider(value: $vm.urgency, in: 0...1)
                                        .onChange(of: vm.urgency) { _, _ in vm.updatePreviewJSON() }
                                    Text(String(format: "Current: %.2f", vm.urgency))
                                        .font(.footnote).foregroundStyle(.secondary)

                                } else if vm.mode == .budget {
                                    Text("Budget ($/gal)").font(.headline)
                                    Slider(value: $vm.budgetPriceCap, in: 1.0...7.0, step: 0.01)
                                        .onChange(of: vm.budgetPriceCap) { _, _ in vm.updatePreviewJSON() }
                                    Text(String(format: "Current: $%.2f", vm.budgetPriceCap))
                                        .font(.footnote).foregroundStyle(.secondary)

                                } else {
                                    Text("Comfort mode").font(.headline)
                                    Text("Prioritize convenience and experience over pure price or shortest distance.")
                                        .foregroundStyle(.secondary)

                                    VStack(alignment: .leading, spacing: 6) {
                                        Bullet("Nearby food")
                                        Bullet("Restroom availability")
                                        Bullet("Convenience store")
                                        Bullet("Well-known brands")
                                        Bullet("Stations open at arrival")
                                    }
                                    .padding(.top, 4)

                                    Toggle("I don’t care about price/distance", isOn: $vm.comfortIDontCare)
                                        .onChange(of: vm.comfortIDontCare) { _, _ in vm.updatePreviewJSON() }
                                        .padding(.top, 6)
                                }
                            }
                        }

                        // Max distance
                        Card {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("Max Distance: \(vm.maxDistanceMiles) miles").font(.headline)

                                Slider(
                                    value: Binding(
                                        get: { Double(vm.maxDistanceMiles) },
                                        set: { vm.maxDistanceMiles = Int($0.rounded()) }
                                    ),
                                    in: 1...50,
                                    step: 1
                                )
                                .onChange(of: vm.maxDistanceMiles) { _, _ in vm.updatePreviewJSON() }
                            }
                        }

                        // Priority
                        Card {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("Priority").font(.headline)
                                Picker("", selection: $vm.priority) {
                                    ForEach(Priority.allCases) { p in
                                        Text(p.rawValue).tag(p)
                                    }
                                }
                                .pickerStyle(.segmented)
                                .onChange(of: vm.priority) { _, _ in vm.updatePreviewJSON() }
                            }
                        }

                        // Brand
                        Card {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack(spacing: 8) {
                                    Text("Brand").font(.headline)
                                    Text("(optional)").foregroundStyle(.secondary)
                                }
                                TextField("e.g. Chevron, Costco, Arco", text: $vm.brandText)
                                    .textInputAutocapitalization(.words)
                                    .autocorrectionDisabled()
                                    .textFieldStyle(.roundedBorder)
                                    .onChange(of: vm.brandText) { _, _ in vm.updatePreviewJSON() }
                            }
                        }

                        // Amenities
                        Card {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("Amenities").font(.headline)
                                Toggle("Food", isOn: $vm.food).onChange(of: vm.food) { _, _ in vm.updatePreviewJSON() }
                                Toggle("Restroom", isOn: $vm.restroom).onChange(of: vm.restroom) { _, _ in vm.updatePreviewJSON() }
                                Toggle("Convenience Store", isOn: $vm.convenienceStore).onChange(of: vm.convenienceStore) { _, _ in vm.updatePreviewJSON() }
                            }
                        }

                        // Location status
                        Card {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Location").font(.headline)

                                if let lat = vm.latitude, let lon = vm.longitude {
                                    Text(String(format: "lat: %.5f\nlon: %.5f", lat, lon))
                                        .font(.system(.footnote, design: .monospaced))
                                        .foregroundStyle(.secondary)
                                } else {
                                    Text("Waiting for location permission / GPS…")
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }

                        // JSON preview
                        Card {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("JSON Preview").font(.headline)
                                Text(vm.requestJSONPreview)
                                    .font(.system(.footnote, design: .monospaced))
                                    .textSelection(.enabled)
                                    .foregroundStyle(.secondary)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }

                        // Results (simple)
                        if let err = vm.errorMessage {
                            Card {
                                Text(err).foregroundStyle(.red)
                            }
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 4)
                    .padding(.bottom, 10)
                }

                Button {
                    Task { await vm.requestStations() }
                } label: {
                    Text(vm.isLoading ? "Loading..." : "Show Recommendations")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .disabled(vm.isLoading)
                .padding(.horizontal)
                .padding(.bottom, 12)
            
                .navigationDestination(isPresented: $vm.showResults) {
                    RecommendationsView(stations: vm.stations)}
            }
            .navigationTitle("Fuel Advisor")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                // start location
                locationManager.requestPermissionAndStart()
            }
            // pipe location -> vm
            .onReceive(locationManager.$latitude) { vm.latitude = $0; vm.updatePreviewJSON() }
            .onReceive(locationManager.$longitude) { vm.longitude = $0; vm.updatePreviewJSON() }
        }

    }
    
}

// MARK: - UI helpers

struct Card<Content: View>: View {
    @ViewBuilder var content: Content
    var body: some View {
        content
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(uiColor: .secondarySystemBackground))
            )
    }
}

struct Bullet: View {
    let text: String
    init(_ text: String) { self.text = text }
    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text("•")
            Text(text).frame(maxWidth: .infinity, alignment: .leading)
        }
        .foregroundStyle(.secondary)
    }
}

#Preview {
    ContentView()
}
