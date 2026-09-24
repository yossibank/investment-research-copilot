import Foundation

struct ResearchQueryRequest: Encodable {
    let question: String
    let topK: Int
}

struct ResearchSource: Decodable, Identifiable {
    let chunkId: String
    let company: String
    let documentName: String
    let page: Int
    let score: Double
    let sourceUrl: String

    var id: String {
        chunkId
    }
}

struct ResearchQueryResponse: Decodable {
    let answer: String
    let isAnswerable: Bool
    let sources: [ResearchSource]
}

struct ResearchStreamEvent: Decodable {
    let type: EventType
    let text: String?
    let requestId: String?
    let retrievalMs: Double?
    let latencyMs: Double?
    let message: String?
    let retrievedSources: [ResearchSource]?

    enum EventType: String, Decodable {
        case metadata
        case textDelta = "text_delta"
        case done
        case error
    }
}
