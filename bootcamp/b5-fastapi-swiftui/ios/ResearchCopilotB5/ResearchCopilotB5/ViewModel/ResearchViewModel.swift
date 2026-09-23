import Foundation

@MainActor
@Observable
final class ResearchViewModel {
    var question = ""
    var answer = ""
    var sources = [ResearchSource]()
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

        isLoading = true
        errorMessage = nil

        defer {
            isLoading = false
        }

        do {
            let response = try await client.research(question: trimmedQuestion)
            answer = response.answer
            sources = response.sources
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
