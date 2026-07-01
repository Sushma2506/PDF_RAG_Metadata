# 📄 PDF RAG with Metadata, Smart Filters, Reranking & Caching

A Retrieval-Augmented Generation (RAG) pipeline that reads documents (PDF, DOCX, PPTX, HTML), extracts text/tables/images with rich metadata, chunks them using a dual-layer strategy, stores them in Pinecone, and answers questions using a local LLM — with Cohere reranking, **automatic metadata filter detection**, and **SQLite query caching** to save tokens.

---

## ✨ Features

- **Multi-format support**: PDF, DOCX, PPTX, HTML, and plain text files
- **GUI File Picker**: Select single or multiple files easily using a native UI popup.
- **Image extraction**: Saves embedded images from PDFs, Word docs, and PowerPoints
- **Rich metadata per chunk**: source file, file type, page/slide number, table index, content type, and `date_ingested`
- **Dual-layer chunking**:
  - Layer 1: `SemanticChunker` — splits on meaning (strategy varies by file type)
  - Layer 2: `RecursiveCharacterTextSplitter` — enforces max chunk size with smart separators
- **Smart filter detection**: LLM automatically extracts metadata filters from natural language questions (e.g. "show me slide 3", "tables from onboarding file", "last 7 days")
- **Pinecone metadata filtering**: Runs pre-filtered vector search using detected filters before reranking
- **Cohere reranking**: Fetches top-20 results, re-ranks using Cohere, passes best 5 to the LLM
- **Local LLM**: Uses Ollama (`gemma3:4b`) — fully offline, no external API needed for text generation
- **Query Caching & Token Tracking**: SQLite database caches previous answers. If the same question is asked, it returns instantly without burning tokens. Token usage is accurately tracked using `tiktoken`.
- **Duplicate prevention**: Checks existing vector count before re-indexing

---

## 🗂️ Project Structure

The project has been modularized for clean architecture:

```
PDF_RAG_Metadata/
├── main.py                # Main application entry point
├── RAG_Metadata.py        # Legacy monolithic script (optional reference)
├── ui/
│   └── file_picker.py     # Native UI file selection
├── utils/
│   ├── Cache.py           # SQLite caching system for LLM responses
│   ├── chunking.py        # Semantic and recursive text splitting
│   ├── file_loader.py     # File reading and parsing logic
│   ├── llm_utils.py       # LLM filter extraction 
│   └── tokenization.py    # Token processing utilities
├── .env                   # API keys (not committed to Git)
├── .gitignore             # Ignores .env, __pycache__, images, output
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone https://github.com/Sushma2506/PDF_RAG_Metadata.git
cd PDF_RAG_Metadata
```

### 2. Install dependencies

Install the required packages using `requirements.txt` or manually:

```bash
pip install -r requirements.txt
```

*(Note: Ensure you have `tiktoken` installed as well for token tracking.)*

### 3. Set up your `.env` file

Create a `.env` file in the project root:

```env
PINECONE_API_KEY=your_pinecone_api_key_here
COHERE_API_KEY=your_cohere_api_key_here
```

### 4. Install and run Ollama

Download from [https://ollama.com](https://ollama.com), then pull the model:

```bash
ollama pull gemma3:4b
```

---

## 🚀 Usage

1. Run the main application:

```bash
python main.py
```

2. A file picker dialog will pop up. Select one or more documents to process.
3. On first run, the script indexes your documents into Pinecone. On subsequent runs, it asks if you want to re-index or use existing vectors.
4. Enter your questions in natural language — the LLM will automatically detect if you're asking about a specific slide, file, table, date, or date range.
5. If you ask a question that was previously answered, it will load instantly from the cache, showing your token savings.
6. Type `quit` to exit. A summary of token usage and cache hits will be displayed.

---

## 🔄 How It Works

```text
User Selects File (ui.file_picker)
   │
   ▼
read_file() (utils.file_loader)
   → Extracts text, tables, images per page/slide
   → Attaches metadata: source, file_type, page/slide, content_type, date_ingested
   │
   ▼
get_text_chunks() (utils.chunking)
   → Layer 1: SemanticChunker 
   → Layer 2: RecursiveCharacterTextSplitter 
   │
   ▼
Pinecone
   → Stores chunks with full metadata as vectors
   │
   ▼
User Question
   │
   ▼
Check Cache (utils.Cache)
   → If found: Return instantly! (Save tokens)
   → If not found: Continue below...
   │
   ▼
extract_filters_from_question() (utils.llm_utils)
   → Detects: source, slide, content_type, date_ingested, days
   │
   ▼
similarity_search_with_score()
   → Top-20 filtered results from Pinecone
   │
   ▼
Cohere rerank()
   → Re-ranks 20 → selects top 5
   │
   ▼
Ollama LLM (gemma3:4b) & Token Tracking
   → Generates answer, counts tokens with tiktoken
   → Saves to SQLite cache (rag_cache.db) for future use
```

---

## 🧠 Smart Filter Detection Examples

| Question | Detected Filter |
|----------|----------------|
| `"What is on slide 3?"` | `{"slide": 3}` |
| `"Show me tables from the onboarding file"` | `{"source": "sample_onboarding", "content_type": "table"}` |
| `"What did we discuss in the last 7 days?"` | `{"days": 7}` |
| `"What is the capital of France?"` | `{}` (no filter — searches everything) |

---

## 🛠️ Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_size` | 1000 | Max characters per chunk |
| `chunk_overlap` | 50 | Overlap between chunks |
| `k` (retrieval) | 20 | Number of chunks fetched from Pinecone before reranking |
| `top_n` (rerank) | 5 | Number of chunks passed to LLM after Cohere reranking |
| Embedding model | `all-MiniLM-L6-v2` | HuggingFace sentence transformer (384 dimensions) |
| Tokenizer | `cl100k_base` | OpenAI tokenizer used for exact token tracking |
| LLM | `gemma3:4b` | Local Ollama model |
| Reranker | `rerank-english-v3.0` | Cohere reranking model |
| Pinecone index | `my-first-rag-1` | Serverless, AWS us-east-1, cosine metric |

---

## 📦 Metadata Fields Stored per Chunk

| Field | Description |
|-------|-------------|
| `source` | Filename without extension |
| `file_type` | `pdf`, `docx`, `pptx`, `html`, etc. |
| `page` | Page number (PDF, DOCX, HTML) |
| `slide` | Slide number (PPTX) |
| `total_pages` / `total_slides` | Total count (PDF / PPTX) |
| `table_num` | Table index (if content is a table) |
| `content_type` | `"table"` for table sections |
| `chunk_index` | e.g. `"2_1"` = semantic chunk 2, sub-chunk 1 |
| `date_ingested` | UTC date when document was indexed |

---

## 📌 Notes

- Pinecone index dimension is `384` (matching `all-MiniLM-L6-v2`)
- Reranking and filter detection require an active internet connection (Cohere API)
- The LLM runs fully locally via Ollama — no data sent to external APIs for text generation
- Database cache is stored locally in `rag_cache.db`.
