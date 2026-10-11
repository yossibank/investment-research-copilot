import Foundation

@MainActor
@Observable
final class ResearchViewModel {
    var question = ""
    var answer = ""
    var sources: [ResearchSource] = []
    var toolsUsed: [String] = []
    var isLoading = false
    var errorMessage: String?

    private let client = APIClient()
}

extension ResearchViewModel {
    func submit() async {
        let trimmedQuestion = question.trimmingCharacters(in: .whitespacesAndNewlines)

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
            let response = try await client.copilot(question: trimmedQuestion)
            answer = response.answer
            sources = response.sources
            toolsUsed = response.toolsUsed
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
