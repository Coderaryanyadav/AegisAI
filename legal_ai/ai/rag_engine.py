from typing import List, Dict, Any, Optional
from legal_ai.ai.ollama_client import LocalOllamaClient
from legal_ai.ai.prompts import (
    LEGAL_ASSISTANT_SYSTEM_PROMPT, 
    RAG_CONTEXT_TEMPLATE,
    CONTRACT_AUDIT_SYSTEM_PROMPT,
    CONTRACT_AUDIT_PROMPT_TEMPLATE,
    LEGAL_DRAFTING_SYSTEM_PROMPT,
    LEGAL_DRAFTING_PROMPT_TEMPLATE,
    TIMELINE_PROMPT_TEMPLATE
)
from legal_ai.document_pipeline.vector_store import LocalVectorStore

class LegalRAGEngine:
    def __init__(self):
        self.ollama = LocalOllamaClient()
        self.vector_store = LocalVectorStore()

    def query(
        self, 
        question: str, 
        document_ids: Optional[List[int]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieves relevant documents, compiles context, queries Ollama,
        and returns the answer with source citations.
        """
        # Retrieve chunks from vector store
        chunks = self.vector_store.query_similarity(
            query=question,
            limit=limit,
            document_ids=document_ids
        )
        
        if not chunks:
            return {
                "answer": "No relevant documents found. Please upload documents first.",
                "citations": []
            }
            
        # Assemble context string
        context_parts = []
        citations = []
        
        for idx, chunk in enumerate(chunks, start=1):
            meta = chunk["metadata"]
            filename = meta.get("original_name", "Unknown File")
            page_num = meta.get("page_number", 1)
            content = chunk["content"]
            
            context_parts.append(
                f"Source [{idx}]: {filename} (Page {page_num})\n"
                f"Content: {content}\n"
                f"----------------------------------------"
            )
            
            citations.append({
                "source_index": idx,
                "document_id": meta.get("document_id"),
                "original_name": filename,
                "page_number": page_num,
                "content": content,
                "score": chunk.get("distance")  # Similarity distance (lower is closer in L2)
            })
            
        context_str = "\n".join(context_parts)
        
        # Build full prompt
        prompt = RAG_CONTEXT_TEMPLATE.format(
            context=context_str,
            question=question
        )
        
        # Query Ollama
        answer = self.ollama.generate(
            prompt=prompt,
            system_prompt=LEGAL_ASSISTANT_SYSTEM_PROMPT
        )
        
        return {
            "answer": answer,
            "citations": citations
        }

    def audit_contract(self, document_id: int) -> Dict[str, Any]:
        """
        Runs a contract audit by retrieving all chunks of a specific document,
        joining them, and executing the auditing prompt against Ollama in JSON format.
        """
        # Retrieve all chunks for the contract to get full context
        # Note: Set a high limit (e.g. 50 chunks) to capture the whole contract
        chunks = self.vector_store.query_similarity(
            query="parties effective date termination indemnification liability governing law dispute resolution",
            limit=50,
            document_ids=[document_id]
        )
        
        if not chunks:
            raise ValueError("No text content found for this document to perform audit.")
            
        # Sort chunks by index to reconstruct document order
        sorted_chunks = sorted(chunks, key=lambda x: x["metadata"].get("chunk_index", 0))
        contract_text = "\n".join([chunk["content"] for chunk in sorted_chunks])
        
        prompt = CONTRACT_AUDIT_PROMPT_TEMPLATE.format(contract_text=contract_text)
        
        response_str = self.ollama.generate(
            prompt=prompt,
            system_prompt=CONTRACT_AUDIT_SYSTEM_PROMPT,
            json_format=True
        )
        
        try:
            import json
            # Verify it is valid JSON
            return json.loads(response_str)
        except Exception as e:
            print(f"[!] Failed to parse audit JSON: {e}. Raw response: {response_str}")
            # Try to recover or wrap raw text
            return {
                "error": "Failed to parse structured audit response. Local model output was not valid JSON.",
                "raw_output": response_str
            }

    def draft_document(
        self, 
        instructions: str, 
        reference_doc_ids: Optional[List[int]] = None
    ) -> str:
        """
        Drafts a new legal document using user instructions and optional context
        retrieved from referenced case/contract files.
        """
        reference_context = "No reference files selected."
        
        if reference_doc_ids:
            # Semantic search to pull reference text relative to instructions
            chunks = self.vector_store.query_similarity(
                query=instructions,
                limit=6,
                document_ids=reference_doc_ids
            )
            if chunks:
                ref_parts = []
                for chunk in chunks:
                    ref_parts.append(
                        f"Ref [{chunk['metadata']['original_name']}, Page {chunk['metadata']['page_number']}]: "
                        f"{chunk['content']}"
                    )
                reference_context = "\n\n".join(ref_parts)
                
        prompt = LEGAL_DRAFTING_PROMPT_TEMPLATE.format(
            instructions=instructions,
            reference_context=reference_context
        )
        
        return self.ollama.generate(
            prompt=prompt,
            system_prompt=LEGAL_DRAFTING_SYSTEM_PROMPT
        )

    def generate_timeline(self, document_ids: List[int]) -> str:
        """
        Analyze documents to construct a chronological event timeline.
        """
        # Pull chunks containing dates or events
        chunks = self.vector_store.query_similarity(
            query="January February March April May June July August September October November December 2020 2021 2022 2023 2024 2025 2026 dates contract agreement occurred signed breached filed dispute",
            limit=15,
            document_ids=document_ids
        )
        
        if not chunks:
            return "No content found to build timeline."
            
        context_parts = []
        for chunk in chunks:
            context_parts.append(
                f"[{chunk['metadata']['original_name']}, Page {chunk['metadata']['page_number']}]: "
                f"{chunk['content']}"
            )
        context_str = "\n\n".join(context_parts)
        
        prompt = TIMELINE_PROMPT_TEMPLATE.format(context=context_str)
        
        return self.ollama.generate(
            prompt=prompt,
            system_prompt=LEGAL_ASSISTANT_SYSTEM_PROMPT
        )
