# Investment Research Copilot

An AI-powered research application for exploring company earnings filings with grounded answers, source attribution, and measurable RAG evaluation.

The project combines a SwiftUI client, FastAPI backend, semantic search, Claude, and a manually curated evaluation set to demonstrate an end-to-end Applied AI workflow.

> This project is for research and educational purposes only. It does not provide investment advice or trading recommendations.

---

## Overview

Investment Research Copilot helps users ask natural-language questions about company earnings documents and receive answers grounded in the original source material.

Instead of sending an entire filing directly to an LLM, the application first retrieves the most relevant document chunks using semantic search and then provides only that evidence to Claude.

The system is designed around three principles:

* Ground answers in primary-source documents.
* Show where the answer came from.
* Measure retrieval and generation quality separately.

---

## Demo Flow

A user can ask a question such as:

```text
What was the company's operating income?
```

The application processes the request as follows:

```text
SwiftUI
   ↓
FastAPI
   ↓
Vector Search
   ↓
Top-K relevant chunks
   ↓
Claude
   ↓
Grounded answer
   ↓
Source document / page
```

The SwiftUI client displays both the generated answer and the retrieved evidence.

---

## Architecture

```text
                    ┌─────────────────────┐
                    │     SwiftUI App     │
                    │                     │
                    │ Question / Answer   │
                    │ Retrieved Evidence  │
                    └──────────┬──────────┘
                               │
                               │ HTTP / NDJSON
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │                     │
                    │ Validation          │
                    │ Request ID          │
                    │ Structured Logging  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      RAG Layer      │
                    │                     │
                    │ Retrieval           │
                    │ Context Building    │
                    │ Claude Generation   │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
       ┌──────────────────┐        ┌──────────────────┐
       │ Semantic Search  │        │      Claude      │
       │                  │        │                  │
       │ multilingual-e5  │        │ Grounded Answer  │
       │ Cosine Similarity│        │ Streaming        │
       └─────────┬────────┘        └──────────────────┘
                 │
                 ▼
       ┌──────────────────┐
       │ Filing Documents │
       │                  │
       │ PDF              │
       │ Page Extraction  │
       │ Chunking         │
       │ Embeddings       │
       └──────────────────┘
```

---

## Features

### Financial Metrics

Deterministic Python functions calculate financial metrics such as:

* Revenue growth
* Operating income growth
* Operating margin
* EPS growth

Financial calculations are intentionally handled in normal Python code rather than delegated to an LLM.

### Structured Filing Extraction

Claude extracts structured financial information from filing text using Pydantic schemas.

Examples include:

* Revenue
* Operating income
* Net income
* Company guidance
* Reporting period
* Source page

Missing information is represented explicitly instead of being guessed.

### Semantic Search

Company filings are:

```text
PDF
 ↓
Page extraction
 ↓
Chunking
 ↓
Embedding
 ↓
Semantic search
```

The current baseline uses:

```text
intfloat/multilingual-e5-small
```

Document chunks are embedded using the `passage:` prefix, while user questions use the `query:` prefix.

Retrieved chunks preserve source metadata including:

* Company
* Document
* Reporting period
* Page
* Source URL
* Chunk ID

### Retrieval-Augmented Generation

The RAG pipeline retrieves the top relevant chunks before generating an answer.

```text
Question
 ↓
Top-K retrieval
 ↓
Context
 ↓
Claude
 ↓
Structured answer
```

Claude is instructed to:

* Use only the supplied context.
* Avoid guessing missing information.
* Preserve numerical values and units.
* Abstain when the source material is insufficient.
* Return source chunk IDs and source pages.

### Answer Abstention

The system explicitly evaluates whether the model can avoid answering questions that cannot be supported by the supplied filing.

For example:

```text
What will the company's stock price be in 2035?
```

should not produce a fabricated prediction.

The expected behavior is to indicate that the answer cannot be confirmed from the provided material.

### FastAPI Backend

The backend exposes the research pipeline through an HTTP API.

Main endpoints:

```text
GET  /health

POST /research/query

POST /research/stream
```

`/research/query` returns a complete structured response.

`/research/stream` streams generated text incrementally to the client.

### SwiftUI Client

The iOS application:

* Sends research questions to FastAPI.
* Decodes structured API responses.
* Displays answers and evidence.
* Handles loading and error states.
* Supports incremental streaming responses.

Anthropic API credentials are never stored in the iOS application.

### Streaming

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

This improves perceived latency by displaying the answer as it is generated rather than waiting for the complete response.

### Observability

Backend requests are logged using structured JSON.

Captured fields include:

* Request ID
* HTTP method
* Endpoint
* Status code
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

User prompts, raw filing contents, API keys, and other sensitive values are not intentionally written to application logs.

---

## RAG Pipeline

The retrieval pipeline currently follows this sequence:

```text
1. Load source PDF

2. Extract text page by page

3. Split each page into overlapping chunks

4. Store source metadata on every chunk

5. Generate normalized embeddings

6. Embed the user query

7. Calculate semantic similarity

8. Select the Top-K chunks

9. Build grounded context

10. Send the context and question to Claude

11. Return answer and evidence
```

The initial chunking baseline uses:

```text
max_chars = 800
overlap = 120
top_k = 5
```

These values are treated as evaluation baselines rather than assumed to be optimal.

---

## Evaluation

RAG quality is evaluated separately at the retrieval, generation, and source-attribution layers.

The current evaluation set contains manually curated questions derived from the source documents.

### Metrics

| Metric            | Score |
| ----------------- | ----: |
| Recall@5          | 90.0% |
| Page Recall@5     | 100.0% |
| Answer Accuracy   | 95.0% |
| Source Match Rate | 90.0% |

Replace these values with the latest measured baseline from:

```text
bootcamp/b4-rag-evaluation/eval/results/latest.json
```

### Recall@5

Recall@5 measures whether the expected evidence chunk appears anywhere in the top five retrieval results.

```text
Expected evidence
       ↓
Top 5 results
       ↓
Found?
```

This primarily evaluates retrieval quality.

### Page Recall@5

Page Recall@5 measures whether a chunk from the expected source page appears in the retrieval results.

This helps distinguish between:

```text
Wrong document/page
```

and:

```text
Correct page but imperfect chunk boundary
```

### Answer Accuracy

Answer Accuracy checks whether the generated answer contains the required facts defined in the Golden Set.

Answerable and unanswerable questions are both evaluated.

For unanswerable questions, correctly abstaining is considered a successful result.

### Source Match Rate

Source Match Rate checks whether the generated response references the expected source evidence.

This is evaluated separately from answer correctness because a correct answer with an incorrect citation is still a quality issue.

---

## Failure Analysis

Evaluation failures are analyzed by pipeline stage.

### Retrieval Error

```text
Expected evidence not found in Top-K.
```

Potential areas to investigate:

* Chunk size
* Chunk overlap
* Embedding model
* Query formulation
* Top-K
* PDF extraction quality

### Generation Error

```text
Correct evidence retrieved,
but the generated answer is incorrect.
```

Potential areas to investigate:

* Prompt instructions
* Context formatting
* Conflicting chunks
* Model behavior
* Structured output constraints

### Source Attribution Error

```text
Answer is correct,
but the cited evidence is incorrect.
```

Potential areas to investigate:

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

A generation problem should not be diagnosed before verifying that the model received the correct evidence.

---

## API

### Health Check

```http
GET /health
```

Example response:

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

### Streaming Research

```http
POST /research/stream
```

The streaming endpoint returns NDJSON events.

Example:

```json
{"type":"metadata","request_id":"abc","retrieved_sources":[]}
{"type":"text_delta","text":"Operating"}
{"type":"text_delta","text":" income was"}
{"type":"text_delta","text":" ..."}
{"type":"done","request_id":"abc","latency_ms":1850}
```

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

### Engineering

* Structured Output
* Retrieval-Augmented Generation
* Semantic Search
* Golden Set Evaluation
* Structured Logging
* Request IDs
* Streaming
* Dependency mocking
* Git / GitHub

---

## Repository Structure

```text
investment-research-copilot/
├── bootcamp/
│   ├── b1-financial-metrics/
│   ├── b2-structured-extraction/
│   ├── b3-vector-search/
│   ├── b4-rag-evaluation/
│   └── b5-fastapi-swiftui/
│
├── README.md
├── learning-log.md
├── .env.example
└── .gitignore
```

The bootcamp directories preserve the incremental learning and implementation history.

The project is intended to evolve into a more integrated application structure as the production-oriented implementation matures.

---

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>

cd investment-research-copilot
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv

source .venv/bin/activate
```

### 3. Install required packages

Install the dependencies used by the relevant bootcamp modules.

For example:

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

Copy:

```text
.env.example
```

to:

```text
.env
```

Then configure:

```text
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
```

Do not commit `.env`.

### 5. Prepare source documents

Raw filing PDFs are intentionally excluded from Git.

Place the required development document under the expected local data directory before running the ingestion pipeline.

### 6. Generate chunks and embeddings

Run the B3 pipeline to:

```text
PDF
 ↓
pages
 ↓
chunks
 ↓
embeddings
```

### 7. Start FastAPI

From the B5 backend directory:

```bash
fastapi dev research_api/main.py
```

The development API is available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### 8. Run the iOS application

Open the Xcode project under the B5 iOS directory and run the app using an iOS Simulator.

The development client is configured to communicate with the local FastAPI backend.

---

## Testing

Run Python tests with:

```bash
python -m pytest
```

Evaluation can first be smoke-tested with a small number of cases:

```bash
python -m rag_evaluation.evaluator --limit 1
```

Then:

```bash
python -m rag_evaluation.evaluator --limit 3
```

Finally run the complete Golden Set:

```bash
python -m rag_evaluation.evaluator
```

This avoids unnecessary API calls while debugging the evaluation pipeline.

---

## Security

The project follows several basic security rules:

* Anthropic API keys are stored only on the backend.
* Secrets are loaded through environment variables.
* `.env` is excluded from Git.
* Raw filing PDFs are excluded from Git.
* Embedding cache files are excluded from Git.
* API keys are not intentionally written to logs.
* LLM-provided source IDs are validated against actual retrieval results.
* Internal exception details are not returned directly to clients.

The iOS application never contains the Anthropic API key.

---

## Data Handling

Source documents remain local during the current development workflow unless explicitly sent to an external API as part of a model request.

Repository metadata may contain:

* Company
* Reporting period
* Document title
* Source URL
* Retrieval date

Raw documents are not committed to the public repository.

---

## Limitations

Current limitations include:

* The evaluation set is intentionally small and manually curated.
* PDF extraction quality may vary, especially for complex financial tables.
* Character-based chunking is currently used as the baseline.
* Semantic retrieval quality depends on the embedding
