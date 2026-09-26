"""SnapAI Edge - RAG (Retrieval-Augmented Generation) API
Uses ChromaDB for local vector store + Jina for embeddings + reranking.
"""

import uuid
import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.db import get_db, Document
from ai.router import router as ai_router
from api.documents import extract_text_from_file

router = APIRouter()

# ─── Chunking ─────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    if not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


# ─── ChromaDB ─────────────────────────────────────────────

def get_chroma_collection(name: str = "snapai_docs"):
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        col = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
        return col, client
    except Exception as e:
        raise HTTPException(500, f"ChromaDB unavailable: {str(e)}")


# ─── Routes ───────────────────────────────────────────────

class IndexRequest(BaseModel):
    doc_id: str
    collection: str = "snapai_docs"


class RAGQuery(BaseModel):
    query: str
    collection: str = "snapai_docs"
    top_k: int = 5
    doc_ids: Optional[list[str]] = None


@router.post("/index")
async def index_document(req: IndexRequest, db: Session = Depends(get_db)):
    """Extract, chunk, embed, and store a document in ChromaDB."""
    doc = db.query(Document).filter_by(id=req.doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    doc.index_status = "indexing"
    db.commit()

    try:
        # Extract text
        text, _ = extract_text_from_file(doc.upload_path, doc.file_type)
        if not text.strip():
            doc.index_status = "error"
            db.commit()
            return {"error": "No text extracted from document"}

        # Chunk
        chunks = chunk_text(text)
        if not chunks:
            doc.index_status = "error"
            db.commit()
            return {"error": "No chunks generated"}

        # Embed via Jina
        embed_result = await ai_router.embed(chunks)
        if "error" in embed_result:
            # Fallback: use simple TF-IDF-like approach or skip embeddings
            doc.index_status = "error"
            db.commit()
            return {"error": f"Embedding failed: {embed_result['error']}"}

        embeddings = embed_result["embeddings"]

        # Store in ChromaDB
        col, _ = get_chroma_collection(req.collection)
        ids = [f"{req.doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": req.doc_id,
                "filename": doc.original_name,
                "file_type": doc.file_type,
                "chunk_index": i,
                "collection": doc.collection,
            }
            for i in range(len(chunks))
        ]

        # Upsert (handle re-indexing)
        col.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        doc.chunk_count = len(chunks)
        doc.indexed = True
        doc.index_status = "ready"
        db.commit()

        return {
            "doc_id": req.doc_id,
            "filename": doc.original_name,
            "chunks": len(chunks),
            "status": "ready",
            "embed_latency_ms": embed_result.get("latency_ms"),
        }
    except Exception as e:
        doc.index_status = "error"
        db.commit()
        raise HTTPException(500, f"Indexing failed: {str(e)}")


@router.post("/query")
async def rag_query(req: RAGQuery, db: Session = Depends(get_db)):
    """Semantic search + rerank + LLM answer generation."""
    # Embed the query
    q_embed = await ai_router.embed_query(req.query)
    if "error" in q_embed:
        raise HTTPException(500, f"Query embedding failed: {q_embed['error']}")

    # Search ChromaDB
    col, _ = get_chroma_collection(req.collection)
    where = None
    if req.doc_ids:
        where = {"doc_id": {"$in": req.doc_ids}}

    results = col.query(
        query_embeddings=[q_embed["embedding"]],
        n_results=min(req.top_k * 2, 20),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs_list = results.get("documents", [[]])[0]
    metas_list = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs_list:
        return {
            "answer": "No relevant documents found in the knowledge base. Please upload and index documents first.",
            "sources": [],
            "mode": "rag",
        }

    # Rerank
    rerank_result = await ai_router.rerank(req.query, docs_list, top_n=req.top_k)
    reranked = rerank_result.get("results", [])

    # Build context from top reranked chunks
    context_parts = []
    sources = []
    for item in reranked[:req.top_k]:
        idx = item.get("index", 0)
        if idx < len(docs_list):
            context_parts.append(docs_list[idx])
            meta = metas_list[idx] if idx < len(metas_list) else {}
            sources.append({
                "filename": meta.get("filename", "Unknown"),
                "chunk": meta.get("chunk_index", idx),
                "score": round(item.get("relevance_score", 1 - distances[idx]), 3),
            })

    context = "\n\n---\n\n".join(context_parts)

    # Generate answer via AI
    messages = [
        {
            "role": "system",
            "content": (
                "You are a document Q&A assistant. Answer the user's question using ONLY the provided context. "
                "If the answer is not in the context, say so clearly. "
                "Be precise and cite which document/section contains the information."
            ),
        },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {req.query}",
        },
    ]

    ai_result = await ai_router.chat(messages)

    return {
        "answer": ai_result.get("content", ""),
        "sources": sources,
        "mode": ai_result.get("mode", "cloud"),
        "model": ai_result.get("model"),
        "latency_ms": ai_result.get("latency_ms"),
        "chunks_retrieved": len(docs_list),
        "chunks_used": len(context_parts),
    }


@router.get("/collections")
async def list_collections():
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        cols = client.list_collections()
        return {"collections": [c.name for c in cols]}
    except Exception as e:
        return {"collections": [], "error": str(e)}


@router.delete("/index/{doc_id}")
async def delete_index(doc_id: str, db: Session = Depends(get_db)):
    """Remove a document's embeddings from ChromaDB."""
    try:
        col, _ = get_chroma_collection()
        # Get all chunk IDs for this doc
        results = col.get(where={"doc_id": doc_id})
        if results and results.get("ids"):
            col.delete(ids=results["ids"])

        doc = db.query(Document).filter_by(id=doc_id).first()
        if doc:
            doc.indexed = False
            doc.index_status = "pending"
            doc.chunk_count = None
            db.commit()

        return {"deleted": doc_id, "chunks_removed": len(results.get("ids", []))}
    except Exception as e:
        raise HTTPException(500, f"Delete index failed: {str(e)}")
