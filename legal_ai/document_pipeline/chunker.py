import re
from typing import List, Dict, Any

class LegalDocumentChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_document(self, text: str, doc_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Splits a document text into structured chunks, keeping track of page numbers
        and document metadata for precise citations.
        """
        chunks = []
        
        # Regex to find page boundaries inserted by the ingestor: "\n--- PAGE X ---\n"
        page_pattern = re.compile(r'\n--- PAGE (\d+) ---\n')
        parts = page_pattern.split(text)
        
        # If no page markers are found (e.g., plain txt files)
        if len(parts) == 1:
            raw_chunks = self._recursive_split(text, self.chunk_size, self.chunk_overlap)
            for idx, content in enumerate(raw_chunks):
                chunks.append({
                    "content": content,
                    "metadata": {
                        "document_id": doc_metadata.get("id"),
                        "original_name": doc_metadata.get("original_name"),
                        "page_number": 1,
                        "chunk_index": idx
                    }
                })
            return chunks

        # Process page by page
        # parts[0] is text before page 1 (usually empty or header)
        # parts[1] is page number "1", parts[2] is text of page 1, and so on.
        global_idx = 0
        header_text = parts[0].strip()
        if header_text:
            raw_chunks = self._recursive_split(header_text, self.chunk_size, self.chunk_overlap)
            for content in raw_chunks:
                chunks.append({
                    "content": content,
                    "metadata": {
                        "document_id": doc_metadata.get("id"),
                        "original_name": doc_metadata.get("original_name"),
                        "page_number": 1,
                        "chunk_index": global_idx
                    }
                })
                global_idx += 1

        for i in range(1, len(parts), 2):
            page_num = int(parts[i])
            page_text = parts[i+1]
            
            raw_chunks = self._recursive_split(page_text, self.chunk_size, self.chunk_overlap)
            for content in raw_chunks:
                chunks.append({
                    "content": content,
                    "metadata": {
                        "document_id": doc_metadata.get("id"),
                        "original_name": doc_metadata.get("original_name"),
                        "page_number": page_num,
                        "chunk_index": global_idx
                    }
                })
                global_idx += 1
                
        return chunks

    def _recursive_split(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Recursively split text by structural delimiters down to chunk_size."""
        delimiters = ["\n\n", "\n", "; ", ". ", " ", ""]
        return self._split_text(text, delimiters, chunk_size, overlap)

    def _split_text(self, text: str, separators: List[str], chunk_size: int, overlap: int) -> List[str]:
        """Internal recursive helper for text splitting."""
        text = text.strip()
        if len(text) <= chunk_size:
            return [text] if text else []

        # Find the best separator to use
        separator = separators[-1]
        for sep in separators:
            if sep in text:
                separator = sep
                break

        # Split the text
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        chunks = []
        current_chunk = []
        current_len = 0

        for part in splits:
            part_len = len(part)
            # Handle cases where a single part exceeds chunk size
            if part_len > chunk_size:
                # If current chunk has data, save it first
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                    current_chunk = []
                    current_len = 0
                # Split the large part recursively with smaller constraints
                large_splits = self._recursive_split(part, chunk_size, overlap)
                chunks.extend(large_splits)
                continue

            if current_len + part_len + (len(separator) if current_chunk else 0) <= chunk_size:
                current_chunk.append(part)
                current_len += part_len + (len(separator) if len(current_chunk) > 1 else 0)
            else:
                # Save the current chunk
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                
                # Setup next chunk with overlap
                overlap_chunk = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    item_len = len(item)
                    if overlap_len + item_len + (len(separator) if overlap_chunk else 0) <= overlap:
                        overlap_chunk.insert(0, item)
                        overlap_len += item_len + (len(separator) if len(overlap_chunk) > 1 else 0)
                    else:
                        break
                        
                current_chunk = overlap_chunk + [part]
                current_len = sum(len(x) for x in current_chunk) + (len(separator) * (len(current_chunk) - 1))

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return [c.strip() for c in chunks if c.strip()]
