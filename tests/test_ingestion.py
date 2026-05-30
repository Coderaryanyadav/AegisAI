import os
import shutil
import tempfile
import pytest

from legal_ai.config import DATA_DIR
from legal_ai.document_pipeline.ingestor import DocumentIngestor
from legal_ai.document_pipeline.chunker import LegalDocumentChunker
from legal_ai.document_pipeline.vector_store import LocalVectorStore

@pytest.fixture
def temp_data_dir():
    # Setup temporary directory for ChromaDB tests
    old_data_dir = os.environ.get("DATABASE_URL")
    temp_dir = tempfile.mkdtemp()
    
    # Override settings in config for testing (by changing environment)
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_dir}/test_db.db"
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)

def test_document_ingestion_and_encryption(temp_data_dir):
    """Verify raw file ingestion, AES-256 encryption, and text extraction."""
    ingestor = DocumentIngestor()
    original_content = b"This is a highly confidential legal document regarding Case ABC-123."
    
    # 1. Encrypt and store
    safe_filename = "test_encrypted_doc.txt"
    file_path = ingestor.encrypt_and_store_file(original_content, safe_filename)
    
    assert os.path.exists(file_path)
    
    # Check that it's encrypted on disk (content does not match plain text)
    with open(file_path, "rb") as f:
        stored_bytes = f.read()
    assert stored_bytes != original_content
    
    # 2. Decrypt and extract text
    extracted_text = ingestor.extract_text(file_path, "original_name.txt")
    assert extracted_text == "This is a highly confidential legal document regarding Case ABC-123."

def test_document_chunking():
    """Verify recursive chunking splits by page markers and tracks page numbers."""
    chunker = LegalDocumentChunker(chunk_size=100, chunk_overlap=20)
    
    # Inject page markers like PyPDF does
    mock_pdf_text = "\n--- PAGE 1 ---\nThis is the content of page one. It has some text. " \
                    "\n--- PAGE 2 ---\nThis is the content of page two. It has more text."
                    
    doc_metadata = {"id": 42, "original_name": "test_contract.pdf"}
    chunks = chunker.split_document(mock_pdf_text, doc_metadata)
    
    assert len(chunks) >= 2
    
    # Verify metadata is correct
    assert chunks[0]["metadata"]["document_id"] == 42
    assert chunks[0]["metadata"]["page_number"] == 1
    
    # Verify page 2 chunks exist
    page_2_chunks = [c for c in chunks if c["metadata"]["page_number"] == 2]
    assert len(page_2_chunks) > 0
    assert "page two" in page_2_chunks[0]["content"]

def test_chroma_vector_store(temp_data_dir):
    """Verify ChromaDB initialization, chunk indexing, search, filtering, and deletion."""
    # Initialize store (creates a collection isolated in test temp dir)
    store = LocalVectorStore(persist_dir=os.path.join(temp_data_dir, "test_chromadb"), collection_name="test_collection")
    
    # Prepare dummy chunks
    chunks = [
        {
            "content": "The agreement was signed between John Doe and Jane Smith on May 10, 2026.",
            "metadata": {
                "document_id": 1,
                "original_name": "agreement_v1.txt",
                "page_number": 1,
                "chunk_index": 0
            }
        },
        {
            "content": "Under Section 4, the lessee agrees to pay a monthly rent of three thousand dollars.",
            "metadata": {
                "document_id": 1,
                "original_name": "agreement_v1.txt",
                "page_number": 2,
                "chunk_index": 1
            }
        },
        {
            "content": "The patent relates to an anti-gravity engine operating on high energy fusion fields.",
            "metadata": {
                "document_id": 2,
                "original_name": "patent_spec.pdf",
                "page_number": 1,
                "chunk_index": 0
            }
        }
    ]
    
    # Index chunks
    store.add_chunks(chunks)
    
    # Run search query on contract terms
    results = store.query_similarity("monthly rent payment amount", limit=2)
    assert len(results) > 0
    # First match should be the rent clause (lower distance or matching context)
    assert "rent" in results[0]["content"]
    
    # Run scoped search query (only search document 2)
    results_scoped = store.query_similarity("agreement signed date", limit=2, document_ids=[2])
    assert len(results_scoped) > 0
    # Even though query is about agreements, it should return patent content since search is scoped to document 2
    assert "patent" in results_scoped[0]["content"]
    
    # Delete vectors for document 1
    store.delete_document_vectors(1)
    
    # Query again for rent
    results_after_delete = store.query_similarity("monthly rent payment", limit=2, document_ids=[1])
    assert len(results_after_delete) == 0
