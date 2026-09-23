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
