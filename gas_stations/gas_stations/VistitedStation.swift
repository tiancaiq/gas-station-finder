//
//  VistitedStation.swift
//  gas_stations
//
//  Created by B Shen on 3/9/26.
//

import Foundation

struct VisitedStation: Codable, Identifiable {
    let id: String
    let name: String
    let brand: String
    let price: Double
    let distanceMiles: Double
    let latitude: Double
    let longitude: Double
    let visitedAt: Date
}
