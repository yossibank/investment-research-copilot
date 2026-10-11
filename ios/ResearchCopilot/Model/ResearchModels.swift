import Foundation

struct ResearchQueryRequest {
    let question: String
    let topK: Int
}

extension ResearchQueryRequest: Encodable {}

struct ResearchSource {
    let chunkId: String
    let company: String
    let documentName: String
    let page: Int
    let score: Double
    let sourceUrl: String
}

extension ResearchSource: Decodable {}

extension ResearchSource: Identifiable {
    var id: String {
        chunkId
    }
}

struct ResearchStreamEvent {
    let type: EventType
    let text: String?
    let requestId: String?
    let retrievalMs: Double?
    let latencyMs: Double?
    let message: String?
    let retrievedSources: [ResearchSource]?
}

extension ResearchStreamEvent {
    enum EventType: String, Decodable {
        case metadata
        case textDelta = "text_delta"
        case done
        case error
    }
}

extension ResearchStreamEvent: Decodable {}

struct CopilotQueryResponse {
    let answer: String
    let isAnswerable: Bool
    let sources: [ResearchSource]
    let toolsUsed: [String]
}

extension CopilotQueryResponse: Decodable {}
