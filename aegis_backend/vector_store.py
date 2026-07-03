import os
import math
import collections
from typing import List, Dict, Any, Optional
import chromadb

from aegis_backend.database import AEGIS_DIR

CHROMA_DIR = os.path.join(AEGIS_DIR, "chroma")
os.makedirs(CHROMA_DIR, exist_ok=True)

class LocalBM25Indexer:
    """Lightweight, 100% offline BM25 ranker for lexical search matching."""
    def __init__(self, corpus: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus # List of Dict containing "id", "text", "metadata"
        self.doc_count = len(corpus)
        self.doc_lengths = [len(doc["text"].split()) for doc in corpus]
        self.avg_doc_len = sum(self.doc_lengths) / max(1, self.doc_count)
        
        # Word frequencies per document
        self.doc_term_freqs = []
        # Global document frequencies for IDF calculation
        self.doc_freqs = collections.defaultdict(int)
        
        # Precomputed IDFs
        self.term_idfs = {}
        self._build_index()

    def _build_index(self):
        for doc in self.corpus:
            terms = doc["text"].lower().split()
            term_freq = collections.defaultdict(int)
            unique_terms = set(terms)
            
            for term in terms:
                term_freq[term] += 1
                
            for term in unique_terms:
                self.doc_freqs[term] += 1
                
            self.doc_term_freqs.append(term_freq)
            
        # Precompute IDF for all unique terms
        for term, df in self.doc_freqs.items():
            self.term_idfs[term] = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        query_terms = query.lower().split()
        scores = []

        for idx, doc in enumerate(self.corpus):
            score = 0.0
            doc_len = self.doc_lengths[idx]
            term_freqs = self.doc_term_freqs[idx]

            for term in query_terms:
                if term not in term_freqs:
                    continue
                
                tf = term_freqs[term]
                idf = self.term_idfs.get(term, 0.0)

                
                # BM25 term weighting formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            if score > 0:
                scores.append((score, doc))

        # Sort descending
        scores.sort(key=lambda x: x[0], reverse=True)
        return [{"score": s, "doc": d} for s, d in scores[:limit]]


from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

class LocalVectorStore:
    """Manages local embedded ChromaDB vector persistence and hybrid RRF rankings."""
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.embedding_function = ONNXMiniLM_L6_V2()
        try:
            self._collection = self.client.get_or_create_collection(
                name="aegis_knowledge_base",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
        except ValueError:
            import logging
            logging.getLogger("aegis_ai.vector_store").info("Recreating collection due to embedding function mismatch.")
            try:
                self.client.delete_collection("aegis_knowledge_base")
            except Exception:
                pass
            self._collection = self.client.get_or_create_collection(
                name="aegis_knowledge_base",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
        self._bm25_cache = {}  # Cache structure: { cache_key: (bm25_indexer, candidates_dict) }

    @property
    def collection(self):
        try:
            if hasattr(self, '_collection'):
                # Try a quick metadata get to verify the collection handle is still valid
                self._collection.get(limit=1)
                return self._collection
        except Exception:
            pass

        # Re-fetch or re-create the collection if it was wiped or deleted from database metadata
        try:
            self._collection = self.client.get_or_create_collection(
                name="aegis_knowledge_base",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
        except Exception:
            self.client = chromadb.PersistentClient(path=CHROMA_DIR)
            self._collection = self.client.get_or_create_collection(
                name="aegis_knowledge_base",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
        self._warm_up_bm25_cache()
        return self._collection

    def _warm_up_bm25_cache(self):
        """Pre-populate the full BM25 index in memory using paginated batches to prevent memory exhaustion."""
        try:
            bm25_corpus = []
            candidates = {}
            limit = 5000
            offset = 0
            
            while True:
                page = self.collection.get(
                    include=["documents", "metadatas"],
                    limit=limit,
                    offset=offset
                )
                if not page or not page["ids"]:
                    break
                
                for idx in range(len(page["ids"])):
                    doc_id = page["ids"][idx]
                    text = page["documents"][idx]
                    meta = page["metadatas"][idx]
                    bm25_corpus.append({
                        "id": doc_id,
                        "text": text,
                        "metadata": meta
                    })
                    candidates[doc_id] = {
                        "id": doc_id,
                        "content": text,
                        "metadata": meta
                    }
                
                if len(page["ids"]) < limit:
                    break
                offset += limit

            if bm25_corpus:
                self._bm25_cache["all"] = (LocalBM25Indexer(bm25_corpus), candidates)
        except Exception as e:
            import logging
            logging.getLogger("aegis_ai.vector_store").warning(f"Failed to warm up BM25 cache: {e}")

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Add legal chunks to ChromaDB.
        Expects list of dicts: { "id": str, "content": str, "metadata": dict }
        """
        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # ChromaDB automatically handles embedding generation using its default model
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        self._bm25_cache.clear()
        self._warm_up_bm25_cache()

    def delete_document_vectors(self, document_id: int):
        """Remove all text chunks matching the document ID."""
        self.collection.delete(
            where={"document_id": document_id}
        )
        self._bm25_cache.clear()
        self._warm_up_bm25_cache()

    def query_similarity(self, query: str, limit: int = 10, document_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Pure semantic vector lookup."""
        where_filter = None
        if document_ids:
            if len(document_ids) == 1:
                where_filter = {"document_id": document_ids[0]}
            else:
                where_filter = {"document_id": {"$in": document_ids}}

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_filter
        )

        output = []
        if results and results["ids"] and results["ids"][0]:
            for idx in range(len(results["ids"][0])):
                output.append({
                    "id": results["ids"][0][idx],
                    "content": results["documents"][0][idx],
                    "metadata": results["metadatas"][0][idx],
                    "distance": results["distances"][0][idx] if results["distances"] else 1.0
                })
        return output

    def query_hybrid(self, query: str, limit: int = 5, document_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Combines Semantic search (ChromaDB) and Lexical search (BM25) via 
        Reciprocal Rank Fusion (RRF) to retrieve legal terms precisely.
        """
        # 1. Fetch search filters
        where_filter = None
        if document_ids:
            if len(document_ids) == 1:
                where_filter = {"document_id": document_ids[0]}
            else:
                where_filter = {"document_id": {"$in": document_ids}}

        # 2. Retrieve candidates for vector search (fetch top 30)
        vector_results = self.query_similarity(query, limit=30, document_ids=document_ids)

        # 3. Retrieve or lookup BM25 Lexical Index from cache
        cache_key = frozenset(document_ids) if document_ids else "all"
        
        if cache_key in self._bm25_cache:
            bm25_indexer, candidates = self._bm25_cache[cache_key]
        elif document_ids and "all" in self._bm25_cache:
            # Optimize: filter the warm "all" index in memory to avoid ChromaDB read latency
            _, global_candidates = self._bm25_cache["all"]
            candidates = {}
            bm25_corpus = []
            for doc_id, item in global_candidates.items():
                if item["metadata"].get("document_id") in document_ids:
                    candidates[doc_id] = item
                    bm25_corpus.append({
                        "id": doc_id,
                        "text": item["content"],
                        "metadata": item["metadata"]
                    })
            bm25_indexer = LocalBM25Indexer(bm25_corpus)
            self._bm25_cache[cache_key] = (bm25_indexer, candidates)
        else:
            # Retrieve from database
            all_docs = self.collection.get(
                where=where_filter,
                include=["documents", "metadatas"]
            )

            if not all_docs or not all_docs["ids"]:
                # Fallback if corpus is empty
                return vector_results[:limit]

            bm25_corpus = []
            candidates = {}
            for idx in range(len(all_docs["ids"])):
                doc_id = all_docs["ids"][idx]
                text = all_docs["documents"][idx]
                meta = all_docs["metadatas"][idx]
                bm25_corpus.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": meta
                })
                candidates[doc_id] = {
                    "id": doc_id,
                    "content": text,
                    "metadata": meta
                }

            # 4. Rank candidates using BM25 lexical scorer
            bm25_indexer = LocalBM25Indexer(bm25_corpus)
            self._bm25_cache[cache_key] = (bm25_indexer, candidates)

        bm25_results = bm25_indexer.search(query, limit=30)

        # 5. Apply Reciprocal Rank Fusion (RRF)
        # RRF formula: Score = Sum( 1 / (60 + Rank) )
        rrf_scores = collections.defaultdict(float)
        active_candidates = dict(candidates)

        # Process vector ranks
        for rank, res in enumerate(vector_results, start=1):
            doc_id = res["id"]
            rrf_scores[doc_id] += 1.0 / (60.0 + rank)
            if doc_id not in active_candidates:
                active_candidates[doc_id] = {
                    "id": doc_id,
                    "content": res["content"],
                    "metadata": res["metadata"]
                }

        # Process BM25 ranks
        for rank, res in enumerate(bm25_results, start=1):
            doc_id = res["doc"]["id"]
            rrf_scores[doc_id] += 1.0 / (60.0 + rank)
            if doc_id not in active_candidates:
                active_candidates[doc_id] = {
                    "id": doc_id,
                    "content": res["doc"]["text"],
                    "metadata": res["doc"]["metadata"]
                }

        # 6. Sort and return top hybrid recommendations
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        fused_output = []
        for doc_id, rrf_score in sorted_ids[:limit * 3]:
            item = active_candidates[doc_id].copy()
            item["rrf_score"] = rrf_score
            fused_output.append(item)

        return self._rerank_with_cross_encoder(query, fused_output, limit)

    def _rerank_with_cross_encoder(
        self, query: str, candidates: List[Dict[str, Any]], limit: int
    ) -> List[Dict[str, Any]]:
        """
        Reranks hybrid RRF candidates using local ONNX embedding similarity
        combined with lexical overlap for improved statutory query precision.
        """
        if not candidates:
            return []

        query_lower = query.lower()
        query_terms = set(query_lower.split())

        try:
            query_emb = self.embedding_function([query])[0]
            query_norm = math.sqrt(sum(x * x for x in query_emb)) or 1.0
        except Exception:
            query_emb = None
            query_norm = 1.0

        # Batch encode all document snippets in a single model call
        snippets = [item.get("content", "")[:512] for item in candidates]
        try:
            doc_embs = self.embedding_function(snippets)
        except Exception:
            doc_embs = [None] * len(candidates)

        scored = []
        for idx, item in enumerate(candidates):
            content = item.get("content", "")
            content_lower = content.lower()
            doc_terms = set(content_lower.split())
            overlap = len(query_terms & doc_terms) / max(len(query_terms), 1)

            semantic_score = 0.0
            if query_emb is not None and doc_embs[idx] is not None:
                try:
                    doc_emb = doc_embs[idx]
                    doc_norm = math.sqrt(sum(x * x for x in doc_emb)) or 1.0
                    dot = sum(a * b for a, b in zip(query_emb, doc_emb))
                    semantic_score = dot / (query_norm * doc_norm)
                except Exception:
                    semantic_score = 0.0

            rrf_score = item.get("rrf_score", 0.0)
            final_score = (0.45 * rrf_score) + (0.35 * semantic_score) + (0.20 * overlap)
            scored.append((final_score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        output = []
        for final_score, item in scored[:limit]:
            result = item.copy()
            result["rerank_score"] = final_score
            output.append(result)
        return output

    def reset_collection(self):
        """Cleans and re-creates active collection handles after disk wipes."""
        try:
            self.client = chromadb.PersistentClient(path=CHROMA_DIR)
            self._collection = self.client.get_or_create_collection(
                name="aegis_knowledge_base",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
            self._bm25_cache.clear()
            self._warm_up_bm25_cache()
        except Exception as e:
            import logging
            logging.getLogger("aegis_ai.vector_store").error(f"Error resetting chroma collection: {e}")

# Shared vector store singleton instance
vector_store = LocalVectorStore()
