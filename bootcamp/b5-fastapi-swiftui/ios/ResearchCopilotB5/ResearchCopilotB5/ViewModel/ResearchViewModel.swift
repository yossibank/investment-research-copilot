import Foundation

@MainActor
@Observable
final class ResearchViewModel {
    var question = ""
    var answer = ""
    var sources = [ResearchSource]()
    var toolsUsed: [String] = []
    var isLoading = false
    var errorMessage: String?

    private let client = APIClient()

    func submit() async {
        let trimmedQuestion = question.trimmingCharacters(
            in: .whitespacesAndNewlines
        )

        guard !trimmedQuestion.isEmpty else {
            return
        }

        answer = ""
        sources = []
        isLoading = true
        errorMessage = nil

        defer {
            isLoading = false
        }

        do {
//            let response = try await client.research(question: trimmedQuestion)
//            answer = response.answer
//            sources = response.sources

//            let stream = client.researchStream(question: trimmedQuestion)
//
//            for try await event in stream {
//                switch event.type {
//                case .metadata:
//                    sources = event.retrievedSources ?? []
//
//                case .textDelta:
//                    answer += event.text ?? ""
//
//                case .done:
//                    break
//
//                case .error:
//                    errorMessage = event.message ?? "Unknown error"
//                }
//            }

            let response = try await client.copilot(question: trimmedQuestion)

            answer = response.answer
            sources = response.sources
            toolsUsed = response.toolsUsed
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
