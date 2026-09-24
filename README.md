# Investment Research Copilot

An AI-powered investment research application for exploring company earnings filings with grounded answers, source attribution, deterministic financial calculations, and measurable RAG evaluation.

The project combines **SwiftUI, FastAPI, semantic search, Claude, structured outputs, streaming, observability, and controlled tool calling** to demonstrate an end-to-end Applied AI workflow.

> This project is for research and educational purposes only.
> It does not provide investment advice, trading recommendations, or definitive stock-price predictions.

---

## Overview

Investment Research Copilot helps users ask natural-language questions about company earnings documents and receive answers grounded in primary-source materials.

Instead of sending an entire filing directly to an LLM, the application:

1. extracts text from source documents,
2. splits the text into searchable chunks,
3. converts those chunks into embeddings,
4. retrieves the most relevant evidence,
5. provides only that evidence to Claude,
6. generates a grounded answer,
7. displays the supporting source information.

The project is built around three principles:

* **Ground answers in primary-source documents**
* **Separate deterministic computation from LLM reasoning**
* **Evaluate retrieval and generation quality independently**

---

## Current Architecture

```text
                       ┌──────────────────────┐
                       │      SwiftUI App     │
                       │                      │
                       │ Question             │
                       │ Answer               │
                       │ Retrieved Evidence   │
                       └──────────┬───────────┘
                                  │
                                  │ HTTP / NDJSON
                                  ▼
                       ┌──────────────────────┐
                       │       FastAPI        │
                       │                      │
                       │ Validation           │
                       │ Request ID           │
                       │ Error Handling       │
                       │ Structured Logging   │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │      RAG Layer       │
                       │                      │
                       │ Vector Retrieval     │
                       │ Context Building     │
                       │ Claude Generation    │
                       └───────┬───────┬──────┘
                               │       │
                    ┌──────────┘       └──────────┐
                    ▼                             ▼
          ┌───────────────────┐        ┌────────────────────┐
          │  Semantic Search  │        │       Claude       │
          │                   │        │                    │
          │ multilingual-e5   │        │ Grounded Answer    │
          │ cosine similarity │        │ Streaming          │
          └─────────┬─────────┘        └────────────────────┘
                    │
                    ▼
          ┌───────────────────┐
          │ Filing Documents  │
          │                   │
          │ PDF Extraction    │
          │ Chunking          │
          │ Embeddings        │
          └───────────────────┘
```

A controlled Tool Calling layer has also been implemented as a focused preview and will be integrated into the main research pipeline during the MVP integration stage.

---

## Features

### Financial Metrics

Deterministic Python functions calculate financial metrics such as:

* Revenue growth
* Operating income growth
* Operating margin
* EPS growth

Financial arithmetic is intentionally handled in normal Python code instead of being delegated to an LLM.

Example:

```text
Previous revenue: 1,000
Current revenue: 1,100

Revenue growth:
10.0%
```

---

## Structured Filing Extraction

Claude extracts structured financial information from filing text using Pydantic schemas.

Examples include:

* Revenue
* Operating income
* Net income
* Company guidance
* Reporting period
* Source page

Missing information is represented explicitly instead of being guessed.

Example output:

```json
{
  "company": "Example Holdings",
  "revenue": {
    "value": 1100.0,
    "unit": "億円",
    "period": "2026年3月期",
    "source_page": null
  },
  "operating_income": {
    "value": 132.0,
    "unit": "億円",
    "period": "2026年3月期",
    "source_page": null
  }
}
```

---

## Semantic Search

Company filings are processed through the following pipeline:

```text
PDF
 ↓
Page Extraction
 ↓
Chunking
 ↓
Embedding
 ↓
Semantic Search
```

The current embedding baseline uses:

```text
intfloat/multilingual-e5-small
```

Document chunks are embedded using the `passage:` prefix, while user questions use the `query:` prefix.

Each chunk preserves source metadata such as:

* Company
* Document name
* Reporting period
* Page
* Source URL
* Chunk ID

---

## Retrieval-Augmented Generation

The RAG pipeline retrieves relevant evidence before asking Claude to generate an answer.

```text
Question
 ↓
Embedding
 ↓
Top-K Retrieval
 ↓
Grounded Context
 ↓
Claude
 ↓
Structured Answer
```

Claude is instructed to:

* use only the supplied context,
* avoid guessing missing information,
* preserve numerical values and units,
* abstain when the source material is insufficient,
* return source chunk IDs and source pages.

---

## Answer Abstention

The system evaluates whether Claude can avoid answering unsupported questions.

For example:

```text
What will the company's stock price be in 2035?
```

The expected behavior is not to fabricate a prediction.

Instead, the system should indicate that the answer cannot be confirmed from the supplied source material.

This behavior is explicitly included in the evaluation dataset.

---

## Tool Calling

A controlled client-side Tool Calling layer has been implemented for deterministic operations.

The first read-only tool is:

```text
calculate_financial_metrics
```

It calculates:

* Revenue growth
* Operating income growth
* Previous operating margin
* Current operating margin

The current Tool Calling flow is:

```text
User Question
      ↓
Claude
      ↓
Tool Required?
   ↙       ↘
 No         Yes
 ↓           ↓
Answer    tool_use
             ↓
        Application
             ↓
       Allowlist Check
             ↓
      Input Validation
             ↓
       Python Function
             ↓
         tool_result
             ↓
           Claude
             ↓
        Final Answer
```

Claude does **not** execute arbitrary Python code.

The application controls which tools are available and validates all generated tool arguments before execution.

The initial tool is intentionally:

* read-only,
* side-effect free,
* deterministic,
* explicitly registered.

### Tool Safety

The Tool Calling layer follows several guardrails:

* Only explicitly registered tools can be executed.
* Unknown tool names are rejected.
* Tool arguments are validated with Pydantic.
* Arbitrary model-generated code is never passed to `eval()` or `exec()`.
* Tool execution is limited to a maximum number of rounds.
* Tool execution errors are returned as controlled `tool_result` messages.
* The initial tool cannot modify external data.

The Tool Calling implementation is currently a focused bootcamp preview. Integration with the main RAG research pipeline is planned for the MVP integration stage.

---

## FastAPI Backend

The backend exposes the research pipeline through HTTP APIs.

Current endpoints include:

```text
GET  /health
POST /research/query
POST /research/stream
```

### Health Check

```http
GET /health
```

Example:

```json
{
  "status": "ok"
}
```

### Research Query

```http
POST /research/query
```

Example request:

```json
{
  "question": "What was operating income?",
  "top_k": 5
}
```

Example response:

```json
{
  "answer": "Operating income was ...",
  "is_answerable": true,
  "sources": [
    {
      "chunk_id": "example-p4-c0",
      "company": "Example Company",
      "document_name": "Earnings Report",
      "page": 4,
      "score": 0.85,
      "source_url": "https://example.com"
    }
  ]
}
```

---

## Streaming

The streaming pipeline uses:

```text
Claude Streaming
 ↓
FastAPI
 ↓
NDJSON
 ↓
URLSession.bytes(for:)
 ↓
SwiftUI
```

This improves perceived latency by displaying generated text incrementally instead of waiting for the full response.

Example stream:

```json
{"type":"metadata","request_id":"abc","retrieved_sources":[]}
{"type":"text_delta","text":"Operating"}
{"type":"text_delta","text":" income was"}
{"type":"text_delta","text":" ..."}
{"type":"done","request_id":"abc","latency_ms":1850}
```

Retrieved evidence shown during streaming represents the context selected by retrieval and should not automatically be interpreted as exact post-generation source attribution.

---

## SwiftUI Client

The iOS client:

* sends research questions to FastAPI,
* decodes structured API responses,
* displays generated answers,
* displays supporting evidence,
* handles loading and error states,
* supports incremental streaming responses.

The iOS application never stores the Anthropic API key.

Application layers are separated as:

```text
SwiftUI View
 ↓
ViewModel
 ↓
APIClient
 ↓
FastAPI
 ↓
RAG / Claude
```

---

## Evaluation

Retrieval quality, answer quality, and source attribution are measured separately.

The current evaluation dataset contains manually curated questions derived from source documents.

### Baseline Metrics

Replace the values below with the latest measured results from:

```text
bootcamp/b4-rag-evaluation/eval/results/latest.json
```

| Metric            | Score |
| ----------------- | ----: |
| Recall@5          | 90.0% |
| Page Recall@5     | 100.0% |
| Answer Accuracy   | 95.0% |
| Source Match Rate | 90.0% |

---

## Recall@5

Recall@5 measures whether the expected evidence chunk appears anywhere in the top five retrieval results.

```text
Question
 ↓
Top 5 retrieval results
 ↓
Expected evidence present?
```

This primarily measures retrieval quality.

---

## Page Recall@5

Page Recall@5 measures whether evidence from the expected page appears in the top retrieval results.

This helps distinguish:

```text
Wrong document or page
```

from:

```text
Correct page but imperfect chunk selection
```

A high Page Recall with lower Chunk Recall can indicate that chunk boundaries need improvement.

---

## Answer Accuracy

Answer Accuracy measures whether the generated answer contains the required factual information defined in the Golden Set.

The current baseline uses rule-based required-term matching.

Both answerable and unanswerable questions are included.

For unsupported questions, correctly abstaining is considered a successful result.

---

## Source Match Rate

Source Match Rate checks whether the generated answer references the expected evidence.

Answer correctness and citation correctness are intentionally evaluated separately.

A correct answer with an incorrect citation is still treated as a quality issue.

---

## Failure Analysis

RAG failures are classified by pipeline stage.

### Retrieval Error

The expected evidence is not present in the Top-K retrieval results.

Potential causes:

* Chunk size
* Chunk overlap
* Embedding quality
* Query formulation
* Top-K configuration
* PDF extraction quality

### Generation Error

The correct evidence was retrieved, but the generated answer is incorrect.

Potential causes:

* Prompt instructions
* Context formatting
* Conflicting evidence
* Model behavior
* Output constraints

### Source Attribution Error

The answer is correct, but the cited evidence is incorrect.

Potential causes:

* Source-selection instructions
* Duplicate evidence
* Context formatting
* Attribution logic

The debugging order is intentionally:

```text
Retrieval
 ↓
Generation
 ↓
Source Attribution
```

Generation quality should not be diagnosed before verifying that the model received the correct evidence.

---

## Tool Calling Failure Analysis

Tool-enabled workflows introduce additional failure categories.

### Tool Selection Error

A tool was required, but Claude did not request it.

### Tool Input Error

Claude selected the correct tool but provided invalid or incomplete arguments.

### Tool Execution Error

The application selected the tool successfully, but execution failed.

### Generation Error

The tool result was correct, but the final answer misrepresented the result.

This follows the same design philosophy as RAG evaluation:

```text
Do not treat every failure as an LLM failure.

Identify the failing pipeline stage first.
```

---

## Observability

Backend requests are recorded using structured JSON logging.

Current observable fields include:

* Request ID
* HTTP method
* Endpoint
* HTTP status
* Total latency
* Retrieval latency
* Top-K
* Input tokens
* Output tokens

Example:

```json
{
  "event": "research_stream_completed",
  "request_id": "example-request-id",
  "latency_ms": 1853.2,
  "retrieval_ms": 41.8,
  "top_k": 5,
  "input_tokens": 3021,
  "output_tokens": 182
}
```

The goal is to make questions such as these answerable:

```text
Which request failed?

Was retrieval slow?

Was Claude generation slow?

Was the context unusually large?

Did token usage increase?
```

---

## Security

The project follows several security rules:

* Anthropic API credentials exist only on the backend.
* Secrets are loaded from environment variables.
* `.env` is excluded from Git.
* Raw filing PDFs are excluded from Git.
* Generated embedding caches are excluded from Git.
* API credentials are not intentionally written to application logs.
* User prompts and raw source contents are not intentionally logged in full.
* LLM-provided source IDs are validated against actual retrieval results.
* Tool names are checked against an explicit allowlist.
* Tool inputs are validated before execution.
* Arbitrary model-generated code is never executed.
* Internal exception details are not returned directly to clients.

---

## Design Principles

Responsibilities are intentionally separated.

```text
LLM
→ language understanding
→ structured extraction
→ grounded generation
→ approved tool selection


Python
→ deterministic financial calculations
→ validation
→ business logic
→ tool execution


Embedding Model
→ semantic retrieval


FastAPI
→ API boundary
→ request validation
→ error handling
→ observability


SwiftUI
→ user experience
→ state management
→ networking
```

A deterministic operation is not delegated to an LLM when normal application code can perform it reliably.

---

## Technology Stack

### AI / Backend

* Python
* FastAPI
* Pydantic
* Anthropic Claude API
* Sentence Transformers
* multilingual-e5-small
* NumPy
* pypdf
* pytest

### iOS

* Swift
* SwiftUI
* URLSession
* Swift Concurrency
* AsyncThrowingStream

### Applied AI

* Structured Outputs
* Retrieval-Augmented Generation
* Semantic Search
* Tool Calling
* Golden Set Evaluation
* Answer Abstention
* Source Attribution
* Streaming
* Structured Logging

---

## Repository Structure

```text
investment-research-copilot/
├── bootcamp/
│   ├── b1-financial-metrics/
│   ├── b2-structured-extraction/
│   ├── b3-vector-search/
│   ├── b4-rag-evaluation/
│   ├── b5-fastapi-swiftui/
│   └── b7-tool-calling/
│
├── README.md
├── learning-log.md
├── .env.example
└── .gitignore
```

The bootcamp directories preserve the incremental implementation and learning history.

A more integrated product structure will be introduced as the MVP matures.

---

## Development Progress

```text
B1
Financial Metrics
      ↓
B2
Structured Extraction
      ↓
B3
Vector Search
      ↓
B4
RAG Evaluation
      ↓
B5
FastAPI + SwiftUI
      ↓
B6
Streaming + Observability
      ↓
B7
Tool Calling
      ↓
B8
Research Copilot MVP Integration
      ↓
B9
Evaluation + Release
```

---

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>

cd investment-research-copilot
```

### 2. Create a virtual environment

```bash
python -m venv .venv

source .venv/bin/activate
```

### 3. Install dependencies

Install the dependencies required by the relevant modules.

Example:

```bash
python -m pip install \
  anthropic \
  fastapi \
  pydantic \
  python-dotenv \
  sentence-transformers \
  numpy \
  pypdf \
  pytest
```

### 4. Configure environment variables

Create:

```text
.env
```

using:

```text
.env.example
```

Expected variables:

```text
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
```

Never commit `.env`.

### 5. Prepare source documents

Raw company filing PDFs are intentionally excluded from Git.

Place development documents in the expected local `data/raw` directory.

### 6. Build retrieval data

Run the B3 ingestion pipeline:

```text
PDF
 ↓
Page Extraction
 ↓
Chunking
 ↓
Embeddings
```

### 7. Start FastAPI

From the B5 backend directory:

```bash
fastapi dev research_api/main.py
```

Development API:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 8. Run the iOS client

Open the Xcode project under the B5 iOS directory and run it using an iOS Simulator.

### 9. Run the Tool Calling demo

From:

```text
bootcamp/b7-tool-calling
```

run:

```bash
python -m tool_calling.cli
```

Example question:

```text
Previous revenue was 1000,
current revenue was 1100,
previous operating income was 110,
and current operating income was 132.

Calculate revenue growth,
operating income growth,
and current operating margin.
```

---

## Testing

Run unit tests with:

```bash
python -m pytest
```

RAG evaluation can first be smoke-tested with:

```bash
python -m rag_evaluation.evaluator --limit 1
```

Then:

```bash
python -m rag_evaluation.evaluator --limit 3
```

Finally:

```bash
python -m rag_evaluation.evaluator
```

Starting with a small evaluation run avoids unnecessary API calls while debugging.

---

## Data Handling

Source documents remain local during the current development workflow unless information is explicitly sent to an external model API as part of a request.

Repository metadata may contain:

* Company
* Reporting period
* Document title
* Source URL
* Retrieval date

Raw filing documents are intentionally excluded from the public repository.

---

## Limitations

Current limitations include:

* The Golden Set is intentionally small and manually curated.
* PDF extraction may be imperfect for complex financial tables.
* The current baseline uses character-based chunking.
* Retrieval quality depends on the embedding model and document structure.
* Rule-based answer evaluation does not capture every semantically equivalent response.
* Streaming evidence represents retrieved context rather than guaranteed post-generation attribution.
* Tool Calling is currently implemented as a focused preview and has not yet been fully integrated with the production RAG pipeline.
* The initial tool supports only deterministic financial calculations.
* The local development backend does not yet provide production authentication or rate limiting.
* AI-generated responses may still be incomplete or incorrect.

All generated information should be verified against original primary-source documents.

---

## Roadmap

Next steps include:

* Integrate RAG and Tool Calling into a unified research pipeline
* Connect Tool Calling to the FastAPI application
* Expose tool-assisted answers in SwiftUI
* Expand the evaluation dataset
* Add tool-use evaluation
* Improve retrieval and chunking
* Add more robust document ingestion
* Add production authentication
* Add rate limiting
* Add cost monitoring
* Improve observability
* Prepare a complete MVP release

---

## Disclaimer

This project is provided for educational and research purposes only.

It does not constitute investment advice, financial advice, trading advice, or a recommendation to buy or sell any security.

AI-generated responses may be incomplete or incorrect.

Users should verify all financial information against original company filings and other authoritative primary sources before making any investment decision.
