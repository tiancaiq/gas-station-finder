import Foundation
import UIKit

enum MapLauncher {
    static func openDirections(latitude: Double, longitude: Double, name: String) {
        let encodedName = name.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? name

        // Google Maps (if installed)
        if let googleURL = URL(string: "comgooglemaps://?q=\(latitude),\(longitude)&center=\(latitude),\(longitude)&zoom=14"),
           UIApplication.shared.canOpenURL(googleURL) {
            UIApplication.shared.open(googleURL)
            return
        }

        // Apple Maps fallback
        if let appleURL = URL(string: "http://maps.apple.com/?ll=\(latitude),\(longitude)&q=\(encodedName)") {
            UIApplication.shared.open(appleURL)
        }
    }
}
