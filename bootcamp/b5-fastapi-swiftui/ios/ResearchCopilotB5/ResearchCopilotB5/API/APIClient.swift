import Foundation

struct APIClient {
    private let baseURL = URL(string: "http://127.0.0.1:8000")!

    func research(
        question: String,
        topK: Int = 5
    ) async throws -> ResearchQueryResponse {
        let url = baseURL.appending(path: "research/query")

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase

        request.httpBody = try encoder.encode(
            ResearchQueryRequest(
                question: question,
                topK: topK
            )
        )

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        return try decoder.decode(
            ResearchQueryResponse.self,
            from: data
        )
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case httpError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            "Invalid server response."

        case let .httpError(statusCode):
            "Server error: \(statusCode)"
        }
    }
}
