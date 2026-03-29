"""
Knowledge Base setup for RAG.
Reads all documents from the me/ folder (PDFs + text files),
chunks them, and stores embeddings in a local ChromaDB collection.
"""

import os
import chromadb
from pypdf import PdfReader

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "knowledge_base"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def load_documents(folder="me"):
    """Load all PDFs and text files from the folder."""
    docs = []
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if text.strip():
                docs.append({"source": filename, "text": text.strip()})
        elif filename.lower().endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            if text.strip():
                docs.append({"source": filename, "text": text.strip()})
    return docs


def build_knowledge_base(folder="me"):
    """Build/rebuild the ChromaDB knowledge base from documents in folder."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete existing collection if it exists, then recreate
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    docs = load_documents(folder)
    all_chunks = []
    all_ids = []
    all_metadatas = []

    for doc in docs:
        chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{doc['source']}_chunk_{i}")
            all_metadatas.append({"source": doc["source"], "chunk_index": i})

    if all_chunks:
        collection.add(
            documents=all_chunks,
            ids=all_ids,
            metadatas=all_metadatas,
        )
        print(
            f"Added {len(all_chunks)} chunks from {len(docs)} documents to knowledge base."
        )
    else:
        print("No documents found to index.")

    return collection


def get_knowledge_base():
    """Get the existing ChromaDB collection (read-only access)."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def search_knowledge_base(query, n_results=3):
    """Search the knowledge base and return the most relevant chunks."""
    collection = get_knowledge_base()
    if collection.count() == 0:
        return []
    results = collection.query(
        query_texts=[query], n_results=min(n_results, collection.count())
    )
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    return [
        {"text": doc, "source": meta.get("source", "unknown")}
        for doc, meta in zip(documents, metadatas)
    ]


if __name__ == "__main__":
    build_knowledge_base()
