import Foundation

struct APIClient {
    private let baseURL = URL(string: "http://127.0.0.1:8000")
}

extension APIClient {
    func researchStream(
        question: String,
        topK: Int = 5
    ) -> AsyncThrowingStream<ResearchStreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let request = try makeRequest(
                        path: "research/stream",
                        question: question,
                        topK: topK
                    )

                    let (bytes, response) = try await URLSession.shared.bytes(for: request)
                    try validate(response)

                    for try await line in bytes.lines where !line.isEmpty {
                        let event = try decoder.decode(
                            ResearchStreamEvent.self,
                            from: Data(line.utf8)
                        )

                        continuation.yield(event)
                    }

                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }

            continuation.onTermination = { _ in
                task.cancel()
            }
        }
    }

    func copilot(
        question: String,
        topK: Int = 5
    ) async throws -> CopilotQueryResponse {
        let request = try makeRequest(
            path: "research/copilot",
            question: question,
            topK: topK
        )

        let (data, response) = try await URLSession.shared.data(for: request)
        try validate(response)

        return try decoder.decode(
            CopilotQueryResponse.self,
            from: data
        )
    }
}

private extension APIClient {
    var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }

    func makeRequest(
        path: String,
        question: String,
        topK: Int
    ) throws -> URLRequest {
        guard let url = baseURL?.appending(path: path) else {
            throw APIError.invalidURL
        }

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(ResearchQueryRequest(question: question, topK: topK))

        return request
    }

    func validate(_ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
    }
}

enum APIError {
    case invalidURL
    case invalidResponse
    case httpError(Int)
}

extension APIError: LocalizedError {
    var errorDescription: String? {
        switch self {
        case .invalidURL: "Invalid server URL."
        case .invalidResponse: "Invalid server response."
        case let .httpError(statusCode): "Server error: \(statusCode)"
        }
    }
}
