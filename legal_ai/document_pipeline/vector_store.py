import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from legal_ai.config import CHROMA_DB_DIR, EMBEDDINGS_MODEL_NAME

class LocalVectorStore:
    def __init__(self):
        # Create a persistent local client for ChromaDB
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        
        # Load local SentenceTransformer model
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDINGS_MODEL_NAME
        )
        
        # Retrieve or create collection
        self.collection = self.client.get_or_create_collection(
            name="legal_documents_v1",
            embedding_function=self.embedding_fn
        )

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Adds text chunks to the ChromaDB vector database.
        """
        if not chunks:
            return
            
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            doc_id = chunk["metadata"]["document_id"]
            chunk_idx = chunk["metadata"]["chunk_index"]
            page_num = chunk["metadata"]["page_number"]
            # Unique ID combination including page number and chunk index
            unique_id = f"doc_{doc_id}_p{page_num}_c{chunk_idx}"
            
            ids.append(unique_id)
            documents.append(chunk["content"])
            # Format metadata (Chroma DB requires simple data types: str, int, float, bool)
            metadatas.append({
                "document_id": int(doc_id),
                "original_name": str(chunk["metadata"]["original_name"]),
                "page_number": int(chunk["metadata"]["page_number"]),
                "chunk_index": int(chunk_idx)
            })
            
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def query_similarity(
        self, 
        query: str, 
        limit: int = 5, 
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries the vector store for semantic matches.
        Optionally filters results to specific document IDs.
        """
        where_filter = None
        if document_ids:
            if len(document_ids) == 1:
                where_filter = {"document_id": int(document_ids[0])}
            else:
                # ChromaDB filter schema for list filtering
                where_filter = {"$or": [{"document_id": int(d_id)} for d_id in document_ids]}

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_filter
        )
        
        formatted_results = []
        if results and results["documents"] and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]
            ids = results["ids"][0]
            
            for idx in range(len(docs)):
                formatted_results.append({
                    "id": ids[idx],
                    "content": docs[idx],
                    "metadata": metas[idx],
                    "distance": distances[idx]
                })
                
        return formatted_results

    def delete_document_vectors(self, document_id: int) -> None:
        """
        Removes all stored vectors associated with a deleted document.
        """
        self.collection.delete(
            where={"document_id": int(document_id)}
        )
