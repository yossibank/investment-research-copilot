import Playgrounds
import SwiftUI

@main
@MainActor
struct MyApp {}

extension MyApp: App {
    var body: some Scene {
        WindowGroup {
            ResearchView()
        }
    }
}

#Playground {
    let a = 1 + 2
    print(a)
}
