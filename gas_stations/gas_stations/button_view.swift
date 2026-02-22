//
//  button_view.swift
//  gas_stations
//
//  Created by B Shen on 2/19/26.
//

import SwiftUI

struct button_view: View {
    var title: String
    var textColor: Color
    var backgroundColor: Color
    var body: some View{
        Text(title)
            .frame(width: 120, height: 60)
            .background(backgroundColor)
            .foregroundColor(textColor)
            .font(.system(size: 20,weight: .bold, design: .default))
            .cornerRadius(10)
        
    }
}

#Preview {
    button_view(title: "test", textColor: .white, backgroundColor: .gray)
}
