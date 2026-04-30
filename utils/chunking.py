from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker

def get_text_chunks(sections, embeddings, chunk_size=1000, chunk_overlap=50):
    all_chunks = []

    for section in sections:
        raw_text = section["text"]
        base_metadata = section["metadata"]

        # ← read THIS section's own file_type from its metadata
        file_type = base_metadata.get("file_type", "txt")

        if not raw_text.strip():
            continue

        # Choose semantic chunker based on THIS section's file type
        if file_type in ("pptx", "pdf", "docx"):
            semantic_splitter = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=95,
            )
        elif file_type in ("html", "htm"):
            semantic_splitter = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="interquartile",
                breakpoint_threshold_amount=1.5,
            )
        else:
            semantic_splitter = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="standard_deviation",
                breakpoint_threshold_amount=3,
            )
            
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",  # paragraph break → try this first
                "\n",  # single line break → try second
                ". ",  # sentence ending → try third
                " ",  # word boundary → try fourth
                "",  # last resort → cut anywhere
            ],
        )

        # Layer 1 → semantic chunking first
        semantic_chunks = semantic_splitter.split_text(raw_text)

        # Layer 2 → split any large chunks further
        for i, sem_chunk in enumerate(semantic_chunks):
            smaller_chunks = splitter.split_text(sem_chunk)

            for j, chunk in enumerate(smaller_chunks):
                all_chunks.append(
                    {
                        "text": chunk,
                        "metadata": {
                            **base_metadata,
                            "chunk_index": f"{i}_{j}",  # e.g. "2_0", "2_1"
                        },
                    }
                )

    return all_chunks
