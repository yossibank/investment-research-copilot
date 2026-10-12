import SwiftUI

struct ResearchView: View {
    @State private var viewModel = ResearchViewModel()

    var body: some View {
        NavigationStack {
            Form {
                Section("Question") {
                    TextField(
                        "営業利益はいくらですか？",
                        text: $viewModel.question,
                        axis: .vertical
                    )

                    Button("Research") {
                        Task {
                            await viewModel.submit()
                        }
                    }
                    .disabled(viewModel.isLoading)
                }

                if viewModel.isLoading {
                    Section {
                        ProgressView("Researching...")
                    }
                }

                if !viewModel.answer.isEmpty {
                    Section("Answer") {
                        Text(viewModel.answer)
                    }
                }

                if !viewModel.toolsUsed.isEmpty {
                    Section("Tools Used") {
                        ForEach(viewModel.toolsUsed, id: \.self) { tool in
                            Label(tool, systemImage: "function")
                        }
                    }
                }

                if !viewModel.sources.isEmpty {
                    Section("Sources") {
                        ForEach(viewModel.sources) { source in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(source.documentName)
                                    .font(.headline)

                                Text(source.company)

                                Text("Page \(source.page)")
                                    .foregroundStyle(.secondary)

                                Text("Score: \(String(format: "%.4f", source.score))")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }

                if let errorMessage = viewModel.errorMessage {
                    Section("Error") {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Research Copilot")
        }
    }
}
