# 📄 PDF RAG with Metadata & Reranking

A Retrieval-Augmented Generation (RAG) pipeline that reads documents (PDF, DOCX, PPTX, HTML), extracts text/tables/images with metadata, chunks them using a dual-layer strategy, stores them in Pinecone, and answers questions using a local LLM with Cohere reranking.

---

## ✨ Features

- **Multi-format support**: PDF, DOCX, PPTX, HTML, and plain text files
- **Image extraction**: Saves embedded images from PDFs, Word docs, and PowerPoints
- **Metadata-aware chunking**: Each chunk stores source file, page/slide number, table info, and content type
- **Dual-layer chunking**:
  - Layer 1: Semantic chunking (via `SemanticChunker`) — splits on meaning
  - Layer 2: Recursive character splitting — ensures no chunk exceeds size limits
- **Pinecone vector store**: Stores and retrieves chunks by semantic similarity
- **Cohere reranking**: Re-ranks top-10 retrieved results to surface the best 5 for the LLM
- **Local LLM**: Uses Ollama (`gemma3:4b`) — no OpenAI API needed
- **Duplicate prevention**: Checks if vectors already exist before re-indexing

---

## 🗂️ Project Structure

```
PDF_RAG_Metadata/
├── RAG_Metadata.py        # Main pipeline script
├── .env                   # API keys (not committed to Git)
├── .gitignore             # Ignores .env, __pycache__, images, output
└── README.md              # This file
```

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd PDF_RAG_Metadata
```

### 2. Install dependencies

```bash
pip install pdfplumber pymupdf python-pptx python-docx pandas pillow beautifulsoup4 \
            langchain langchain-text-splitters langchain-experimental \
            langchain-huggingface langchain-ollama langchain-pinecone \
            pinecone-client cohere python-dotenv
```

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

1. Update the `file_path` variable in `RAG_Metadata.py` to point to your document:

```python
file_path = r"C:\path\to\your\document.pptx"
```

2. Run the script:

```bash
python RAG_Metadata.py
```

3. On first run, the script indexes your document into Pinecone. On subsequent runs, it asks if you want to re-index or use existing vectors.

4. Enter your questions in the prompt — type `quit` to exit.

---

## 🔄 How It Works

```
Document
   │
   ▼
read_file()          → Extracts text, tables, images; returns list of {text, metadata} sections
   │
   ▼
get_text_chunks()    → Layer 1: SemanticChunker (splits by meaning)
                     → Layer 2: RecursiveCharacterTextSplitter (enforces size limits)
   │
   ▼
Pinecone             → Stores chunks with metadata as vectors
   │
   ▼
similarity_search()  → Retrieves top-10 most relevant chunks
   │
   ▼
Cohere rerank()      → Re-ranks results, selects top 5
   │
   ▼
Ollama LLM           → Generates answer from reranked context
```

---

## 🛠️ Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_size` | 1000 | Max characters per chunk |
| `chunk_overlap` | 50 | Overlap between chunks |
| `k` (retrieval) | 10 | Number of chunks fetched from Pinecone |
| `top_n` (rerank) | 5 | Number of chunks passed to LLM after reranking |
| Embedding model | `all-MiniLM-L6-v2` | HuggingFace sentence transformer |
| LLM | `gemma3:4b` | Local Ollama model |
| Reranker | `rerank-english-v3.0` | Cohere reranking model |

---

## 📌 Notes

- The Pinecone index dimension is `384` (matching `all-MiniLM-L6-v2`)
- Reranking requires an active internet connection (Cohere API)
- The LLM runs fully locally via Ollama — no data sent to OpenAI
