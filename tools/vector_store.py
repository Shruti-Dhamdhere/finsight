import os
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import config

# Initialize embedding model once (runs locally, free)
print("Loading embedding model...")
EMBEDDING_MODEL = SentenceTransformer(config.EMBEDDING_MODEL)
print("Embedding model ready.")


def chunk_text(text: str, chunk_size: int = config.CHUNK_SIZE,
               overlap: int = config.CHUNK_OVERLAP) -> List[str]:
    """Split long text into overlapping chunks for RAG."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > chunk_size * 0.7:
                end = start + last_period + 1
                chunk = text[start:end]
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return [c for c in chunks if len(c) > 50]


def build_vector_store(ticker: str, filings: List[Dict]) -> chromadb.Collection:
    """
    Build ChromaDB vector store from SEC filings.
    Each chunk is embedded and stored with metadata.
    """
    print(f"  [RAG Agent] Building vector store for {ticker}...")
    
    # Create persistent ChromaDB client
    os.makedirs(config.CHROMA_DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    
    # Delete existing collection for this ticker (fresh data)
    collection_name = f"sec_{ticker.lower()}"
    try:
        client.delete_collection(collection_name)
    except:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        metadata={"ticker": ticker}
    )
    
    all_chunks = []
    all_ids = []
    all_metadata = []
    
    for filing in filings:
        chunks = chunk_text(filing["text"])
        print(f"  [RAG Agent] {filing['type']} ({filing['date']}): {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{filing['type']}_{filing['date']}_{i}")
            all_metadata.append({
                "filing_type": filing["type"],
                "date": filing["date"],
                "chunk_index": i
            })
    
    # Embed all chunks in batches
    print(f"  [RAG Agent] Embedding {len(all_chunks)} chunks...")
    batch_size = 32
    all_embeddings = []
    
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        embeddings = EMBEDDING_MODEL.encode(batch).tolist()
        all_embeddings.extend(embeddings)
    
    # Store in ChromaDB
    collection.add(
        documents=all_chunks,
        embeddings=all_embeddings,
        ids=all_ids,
        metadatas=all_metadata
    )
    
    print(f"  [RAG Agent] Vector store built: {len(all_chunks)} chunks indexed")
    return collection


def query_vector_store(ticker: str, query: str,
                       top_k: int = config.TOP_K_RESULTS) -> List[Dict]:
    """
    Retrieve most relevant chunks for a given query.
    This is the core RAG retrieval step.
    """
    try:
        client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        collection = client.get_collection(f"sec_{ticker.lower()}")
        
        # Embed the query
        query_embedding = EMBEDDING_MODEL.encode([query]).tolist()
        
        # Retrieve top-k most similar chunks
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, collection.count())
        )
        
        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            chunks.append({
                "text": doc,
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        
        return chunks
        
    except Exception as e:
        print(f"  [RAG Agent] Query failed: {e}")
        return []


def get_sec_insights(ticker: str, filings_data: Dict) -> Dict:
    """
    Full RAG pipeline: build store + query key financial topics.
    Returns structured insights from SEC filings.
    """
    if filings_data.get("status") != "success":
        return {"error": "No filing data available", "status": "failed"}
    
    # Build vector store
    collection = build_vector_store(ticker, filings_data["filings"])
    
    # Query key topics investors care about
    queries = {
        "risk_factors": "major risk factors business risks challenges threats",
        "revenue_growth": "revenue growth sales performance financial results",
        "guidance": "forward guidance outlook future expectations forecast",
        "competition": "competition competitive landscape market position",
        "innovation": "new products innovation research development pipeline"
    }
    
    insights = {}
    for topic, query in queries.items():
        chunks = query_vector_store(ticker, query)
        if chunks:
            # Combine top chunks into context
            context = " ".join([c["text"] for c in chunks[:3]])
            insights[topic] = context[:1000]  # Cap at 1000 chars per topic
    
    return {
        "ticker": ticker,
        "insights": insights,
        "total_chunks_indexed": collection.count(),
        "status": "success"
    }