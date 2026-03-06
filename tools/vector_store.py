import os
import time
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import config

# Initialize embedding model once at startup
print("Loading embedding model...")
EMBEDDING_MODEL = SentenceTransformer(config.EMBEDDING_MODEL)
print("Embedding model ready.")

# Single persistent ChromaDB client — created once, reused forever
os.makedirs(config.CHROMA_DB_PATH, exist_ok=True)
_chroma_client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)

# How long before we consider filings stale and re-fetch (7 days)
COLLECTION_TTL_SECONDS = 7 * 24 * 60 * 60


def chunk_text(text: str, chunk_size: int = config.CHUNK_SIZE,
               overlap: int = config.CHUNK_OVERLAP) -> List[str]:
    """Split long text into overlapping chunks for RAG."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > chunk_size * 0.7:
                end = start + last_period + 1
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if len(c) > 50]


def _collection_is_fresh(collection_name: str) -> bool:
    """
    Returns True if the collection exists and was built within COLLECTION_TTL_SECONDS.
    Checks metadata for a 'built_at' timestamp we store on creation.
    """
    try:
        col = _chroma_client.get_collection(collection_name)
        if col.count() == 0:
            return False
        built_at = col.metadata.get("built_at", 0)
        age = time.time() - float(built_at)
        is_fresh = age < COLLECTION_TTL_SECONDS
        if is_fresh:
            print(f"  [RAG Agent] Using cached vector store ({int(age/3600)}h old, {col.count()} chunks)")
        return is_fresh
    except Exception:
        return False


def build_vector_store(ticker: str, filings: List[Dict]) -> chromadb.Collection:
    """
    Build ChromaDB vector store from SEC filings.
    Skips rebuild if a fresh collection already exists on disk.
    """
    collection_name = f"sec_{ticker.lower()}"

    # ── Cache hit: collection exists and is < 7 days old ──────────────────────
    if _collection_is_fresh(collection_name):
        return _chroma_client.get_collection(collection_name)

    # ── Cache miss: build fresh ────────────────────────────────────────────────
    print(f"  [RAG Agent] Building vector store for {ticker}...")

    # Delete stale collection if it exists
    try:
        _chroma_client.delete_collection(collection_name)
    except Exception:
        pass

    collection = _chroma_client.create_collection(
        name=collection_name,
        metadata={
            "ticker":   ticker,
            "built_at": str(time.time()),   # timestamp for freshness check
        }
    )

    all_chunks    = []
    all_ids       = []
    all_metadata  = []

    for filing in filings:
        chunks = chunk_text(filing["text"])
        print(f"  [RAG Agent] {filing['type']} ({filing['date']}): {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{filing['type']}_{filing['date']}_{i}")
            all_metadata.append({
                "filing_type": filing["type"],
                "date":        filing["date"],
                "chunk_index": i,
            })

    print(f"  [RAG Agent] Embedding {len(all_chunks)} chunks...")
    batch_size     = 32
    all_embeddings = []
    for i in range(0, len(all_chunks), batch_size):
        batch      = all_chunks[i:i + batch_size]
        embeddings = EMBEDDING_MODEL.encode(batch).tolist()
        all_embeddings.extend(embeddings)

    collection.add(
        documents  = all_chunks,
        embeddings = all_embeddings,
        ids        = all_ids,
        metadatas  = all_metadata,
    )

    print(f"  [RAG Agent] Vector store built: {len(all_chunks)} chunks indexed")
    return collection


def query_vector_store(ticker: str, query: str,
                       top_k: int = config.TOP_K_RESULTS) -> List[Dict]:
    """Retrieve most relevant chunks for a given query."""
    try:
        collection      = _chroma_client.get_collection(f"sec_{ticker.lower()}")
        query_embedding = EMBEDDING_MODEL.encode([query]).tolist()
        results         = collection.query(
            query_embeddings = query_embedding,
            n_results        = min(top_k, collection.count()),
        )
        return [
            {
                "text":     doc,
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
            for i, doc in enumerate(results["documents"][0])
        ]
    except Exception as e:
        print(f"  [RAG Agent] Query failed: {e}")
        return []


def get_sec_insights(ticker: str, filings_data: Dict) -> Dict:
    """
    Full RAG pipeline: build/load store + query key financial topics.
    First call per ticker: slow (fetch + embed).
    Subsequent calls within 7 days: fast (load from disk + query).
    """
    if filings_data.get("status") != "success":
        return {"error": "No filing data available", "status": "failed"}

    collection = build_vector_store(ticker, filings_data["filings"])

    queries = {
        "risk_factors":   "major risk factors business risks challenges threats",
        "revenue_growth": "revenue growth sales performance financial results",
        "guidance":       "forward guidance outlook future expectations forecast",
        "competition":    "competition competitive landscape market position",
        "innovation":     "new products innovation research development pipeline",
    }

    insights = {}
    for topic, query in queries.items():
        chunks = query_vector_store(ticker, query)
        if chunks:
            context          = " ".join([c["text"] for c in chunks[:3]])
            insights[topic]  = context[:1000]

    return {
        "ticker":               ticker,
        "insights":             insights,
        "total_chunks_indexed": collection.count(),
        "status":               "success",
    }