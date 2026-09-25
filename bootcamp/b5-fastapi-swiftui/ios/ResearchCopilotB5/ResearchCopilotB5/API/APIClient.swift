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

    func researchStream(
        question: String,
        topK: Int = 5
    ) -> AsyncThrowingStream<ResearchStreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let url = baseURL.appending(path: "research/stream")

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

                    let (bytes, response) = try await URLSession.shared.bytes(for: request)

                    guard let httpResponse = response as? HTTPURLResponse else {
                        throw APIError.invalidResponse
                    }

                    guard (200..<300).contains(httpResponse.statusCode) else {
                        throw APIError.httpError(httpResponse.statusCode)
                    }

                    let decoder = JSONDecoder()
                    decoder.keyDecodingStrategy = .convertFromSnakeCase

                    for try await line in bytes.lines {
                        guard !line.isEmpty else {
                            continue
                        }

                        let data = Data(line.utf8)

                        let event = try decoder.decode(
                            ResearchStreamEvent.self,
                            from: data
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
        let url = baseURL.appending(path: "research/copilot")

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
            CopilotQueryResponse.self,
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
