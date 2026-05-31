import os
import math
import collections
from typing import List, Dict, Any, Optional
import chromadb

USER_HOME = os.path.expanduser("~")
AEGIS_DIR = os.path.join(USER_HOME, ".aegis_ai")
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

    def calculate_idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        # Standard BM25 IDF formula with smoothing
        return math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)

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
                idf = self.calculate_idf(term)
                
                # BM25 term weighting formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            if score > 0:
                scores.append((score, doc))

        # Sort descending
        scores.sort(key=lambda x: x[0], reverse=True)
        return [{"score": s, "doc": d} for s, d in scores[:limit]]


from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

class OfflineHashingEmbeddingFunction(EmbeddingFunction):
    """
    A 100% offline, zero-network, zero-dependency embedding function that generates
    deterministic 384-dimensional semantic-lexical vectors via word hashing.
    """
    def __call__(self, input: Documents) -> Embeddings:
        import hashlib
        embeddings = []
        for text in input:
            vector = [0.0] * 384
            # Tokenize and hash
            words = text.lower().split()
            for word in words:
                # MD5 hash of the word to index into 384 dimensions
                h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
                idx = h % 384
                vector[idx] += 1.0
            # L2 Normalize
            norm = sum(x*x for x in vector) ** 0.5
            if norm > 0:
                vector = [x / norm for x in vector]
            embeddings.append(vector)
        return embeddings

class LocalVectorStore:
    """Manages local embedded ChromaDB vector persistence and hybrid RRF rankings."""
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.embedding_function = OfflineHashingEmbeddingFunction()
        try:
            self.collection = self.client.get_or_create_collection(
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
            self.collection = self.client.get_or_create_collection(
                name="aegis_knowledge_base",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
        self._bm25_cache = {}  # Cache structure: { cache_key: (bm25_indexer, candidates_dict) }

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

    def delete_document_vectors(self, document_id: int):
        """Remove all text chunks matching the document ID."""
        self.collection.delete(
            where={"document_id": document_id}
        )
        self._bm25_cache.clear()

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
        else:
            # Retrieve ALL scoped documents to build the BM25 Lexical Index
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
        for doc_id, rrf_score in sorted_ids[:limit]:
            item = active_candidates[doc_id].copy()
            item["rrf_score"] = rrf_score
            fused_output.append(item)

        return fused_output
