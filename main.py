from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import os
import sys
import time

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
import cohere

# Import our modularized backend and UI
from ui.file_picker import pick_file
from utils.file_loader import read_file
from utils.chunking import get_text_chunks
from utils.llm_utils import extract_filters_from_question
from utils.Cache import init_cache, get_cached_answer, save_to_cache

import tiktoken


# loading .env file (must be first)
load_dotenv(verbose=True)

# Reconfigure stdout to handle utf-8 characters properly in Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":

    init_cache()

    # ── Session tracking variables ──
    session_tokens_used = 0  # tokens consumed this session
    session_tokens_saved = 0  # tokens saved by cache
    session_questions = 0  # questions answered by LLM
    session_cache_hits = 0  # questions answered by cache

    # Step 1: Pick files using GUI popup — supports multiple files
    file_paths = pick_file()

    # Process each file and collect all sections together
    all_sections = []

    for file_path in file_paths:
        print(f"\n📄 Reading: {file_path}")

        this_file_type = file_path.split(".")[-1].lower()

        sections = read_file(file_path)

        for section in sections:
            section["metadata"]["file_type"] = this_file_type

        all_sections.extend(sections)
        print(f"   → {len(sections)} sections extracted")

    print(f"\n✅ Total sections from all files: {len(all_sections)}")

    # Step 2: Setup embeddings and LLM
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    chunks = get_text_chunks(all_sections, embeddings)

    llm = OllamaLLM(model="gemma3:4b")

    # Load Gemma tokenizer for exact token counting
    tokenizer = tiktoken.get_encoding("cl100k_base")

    co = cohere.Client(os.getenv("COHERE_API_KEY"))

    # Step 3: Create/connect to Pinecone index
    index_name = "my-first-rag-1"
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    if not pc.has_index(index_name):
        pc.create_index(
            name=index_name,
            dimension=384,  # all-MiniLM-L6-v2 dimensions
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    index = pc.Index(index_name)

    # Step 4: Create vector store and only add text if index is empty
    vectorstore = PineconeVectorStore(index=index, embedding=embeddings)

    # Check if we already have vectors in the index to avoid duplicates
    stats = index.describe_index_stats()
    vector_count = stats.get("total_vector_count", 0)

    if vector_count > 0:
        choice = input(
            f"Index contains {vector_count} vectors. Would you like to clear it and re-index? (y/n): "
        )
        if choice.lower() == "y":
            print("Clearing index...")
            index.delete(delete_all=True)
            print("Waiting for index to clear", end="")
            for attempt in range(20):
                time.sleep(2)
                stats = index.describe_index_stats()
                vector_count = stats.get("total_vector_count", 0)
                print(".", end="", flush=True)
                if vector_count == 0:
                    break

            print(f" done! ({vector_count} vectors remaining)")
            vector_count = 0
            time.sleep(10)

    if vector_count == 0:
        print(f"Indexing {len(chunks)} chunks...")
        vectorstore.add_texts(
            texts=[c["text"] for c in chunks], metadatas=[c["metadata"] for c in chunks]
        )
        print("Indexing complete.")
    else:
        print(f"Skipping indexing. Using existing {vector_count} vectors.")

    # Step 5: Create retriever for querying
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    # Step 6: Query loop
    while True:
        question = input("\nEnter your question (or 'quit' to exit): ")

        if question.lower() in ["exit", "quit", "bye", "goodbye", "q"]:
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("📊 SESSION SUMMARY")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"  Total questions asked : {session_questions + session_cache_hits}")
            print(f"  Answered by LLM       : {session_questions}")
            print(f"  Answered by cache     : {session_cache_hits}")
            print(f"  Tokens burnt          : {session_tokens_used:,}")
            print(f"  Tokens saved by cache : {session_tokens_saved:,}")
            print(
                f"  Total tokens          : {session_tokens_used + session_tokens_saved:,}"
            )
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("Goodbye! 👋")
            break

        # ── CHECK CACHE FIRST ──
        cached = get_cached_answer(question)

        if cached:
            answer, retrieval_secs, generation_secs, total_secs, tokens_per_request = (
                cached
            )
            print("\n⚡ Answer from cache (no tokens used!)")
            print(f"\nAnswer: {answer}")
            print(f"\n⏱️  Last run took: {total_secs:.2f}s")
            print(f"📊 Tokens saved: ~{tokens_per_request:,}")
            session_tokens_saved += tokens_per_request
            session_cache_hits += 1
            continue  # ← skip everything, go back to question prompt

        # ── AUTO-DETECT filters from the question ──
        detected = extract_filters_from_question(question, llm)

        # ── Build Pinecone filter from detected values ──
        pinecone_filter = {}

        if detected.get("source"):
            pinecone_filter["source"] = {"$eq": detected["source"]}

        if detected.get("slide"):
            pinecone_filter["slide"] = {"$eq": int(detected["slide"])}

        if detected.get("content_type"):
            pinecone_filter["content_type"] = {"$eq": detected["content_type"]}

        if detected.get("date_ingested"):
            pinecone_filter["date_ingested"] = {"$eq": detected["date_ingested"]}

        if detected.get("days"):
            days_ago = int(detected["days"])
            date_range = [
                (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(days_ago)
            ]
            pinecone_filter["date_ingested"] = {"$in": date_range}

        search_filter = pinecone_filter if pinecone_filter else None

        start = time.time()

        # Retrieve the most similar text WITH SCORES
        retrieved_documents = vectorstore.similarity_search_with_score(
            question, k=20, filter=search_filter
        )

        if not retrieved_documents:
            print("⚠️  No results found with that filter. Try removing the filter.")
            continue

        # Re-rank the results using Cohere
        rerank_results = co.rerank(
            query=question,
            documents=[doc.page_content for doc, score in retrieved_documents],
            top_n=5,
            model="rerank-english-v3.0",
        )

        # Build reranked list in new order
        reranked_documents = [
            retrieved_documents[result.index] for result in rerank_results.results
        ]

        retrieval_time = time.time()

        context = "\n\n".join([doc.page_content for doc, score in reranked_documents])

        print(f"\n📊 Context stats:")
        print(f"  Chunks: {len(retrieved_documents)}")
        print(f"  Characters: {len(context):,}")
        # print(f"  Estimated tokens: ~{len(context) // 4:,}")

        # Generate response using context with a stricter prompt
        prompt = f"""You are a helpful assistant. Use ONLY the following pieces of context to answer the question at the end.

        IMPORTANT: Read through ALL the context carefully. The answer might be anywhere in the context, not just at the beginning.
        If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.

        Context:
        {context}

        Question: {question}

        Think step by step:
        1. What exactly is the question asking for?
        2. Search through the context for the specific answer
        3. Provide only the answer that directly addresses the question

        Answer:"""

        response = llm.invoke(prompt)
        generation_time = time.time()
        print(f"\n⏱️ TIMING:")
        print(f"  Retrieval: {retrieval_time - start:.2f}s")
        print(f"  Generation: {generation_time - retrieval_time:.2f}s")
        print(f"  Total: {generation_time - start:.2f}s")
        print(f"\nAnswer: {response}")

        # ── CALCULATE EXACT TOKENS USING GEMMA TOKENIZER ──
        prompt_tokens = len(tokenizer.encode(prompt))  # exact tokens sent
        response_tokens = len(tokenizer.encode(response))  # exact tokens received
        total_tokens = prompt_tokens + response_tokens  # total burnt

        # ── SHOW TOKEN USAGE TO USER ──
        print(f"\n🔥 TOKENS BURNT THIS REQUEST:")
        print(f"  Prompt tokens:   {prompt_tokens:,}")
        print(f"  Response tokens: {response_tokens:,}")
        print(f"  Total tokens:    {total_tokens:,}")

        # ── SAVE TO CACHE for next time ──
        save_to_cache(
            question=question,
            answer=response,
            retrieval_secs=retrieval_time - start,
            generation_secs=generation_time - retrieval_time,
            total_secs=generation_time - start,
            tokens_per_request=total_tokens,
        )
        print("💾 Answer saved to cache.")

        # ── UPDATE SESSION TOTALS ──
        session_tokens_used += total_tokens
        session_questions += 1
