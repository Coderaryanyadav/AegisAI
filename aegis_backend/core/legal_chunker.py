import re
from typing import List

class LegalChunker:
    # Regexes for markers
    MARKER_PATTERNS = {
        "chapter": re.compile(r"^\s*(Chapter|Ch\.?|PART)\s+([IVXLCDM\d]+)(?::|\.|\s|$)", re.IGNORECASE),
        "section": re.compile(r"^\s*(Section|Sec\.?|§)\s+(\d+)(?::|\.|\s|$)", re.IGNORECASE),
        "article": re.compile(r"^\s*(Article|Art\.?)\s+(\d+)(?::|\.|\s|$)", re.IGNORECASE),
        "clause": re.compile(r"^\s*(Clause)\s+(\d+(?:\.\d+)*)(?::|\.|\s|$)", re.IGNORECASE),
    }

    @classmethod
    def split_legal_text(cls, text: str, document_name: str = "", chunk_size: int = 400, chunk_overlap: int = 80) -> List[str]:
        if not text:
            return []
            
        lines = text.splitlines()
        
        current_headers = {
            "chapter": "",
            "section": "",
            "article": "",
            "clause": ""
        }
        
        segments = []
        current_segment_lines = []
        
        for line in lines:
            matched_any = False
            for header_type, pattern in cls.MARKER_PATTERNS.items():
                match = pattern.match(line)
                if match:
                    # Save existing segment
                    if current_segment_lines:
                        segments.append({
                            "headers": dict(current_headers),
                            "text": "\n".join(current_segment_lines).strip()
                        })
                        current_segment_lines = []
                    
                    # Update active header
                    marker_name = match.group(1).strip()
                    marker_val = match.group(2).strip()
                    current_headers[header_type] = f"{marker_name} {marker_val}"
                    
                    # Clear child headers when parent changes
                    if header_type == "chapter":
                        current_headers["section"] = ""
                        current_headers["article"] = ""
                        current_headers["clause"] = ""
                    elif header_type in ("section", "article"):
                        current_headers["clause"] = ""
                        
                    matched_any = True
                    break
            
            current_segment_lines.append(line)
            
        if current_segment_lines:
            segments.append({
                "headers": dict(current_headers),
                "text": "\n".join(current_segment_lines).strip()
            })

        # Now sub-chunk the segments if they exceed chunk_size words
        final_chunks = []
        for seg in segments:
            # Build prefix header
            prefixes = []
            if document_name:
                prefixes.append(f"Doc: {document_name}")
            for k in ["chapter", "section", "article", "clause"]:
                if seg["headers"][k]:
                    prefixes.append(seg["headers"][k])
            
            prefix_str = "".join(f"[{p}] " for p in prefixes)

            # Chunk the segment text
            words = seg["text"].split()
            if not words:
                continue
                
            i = 0
            while i < len(words):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                final_chunks.append(f"{prefix_str}{chunk_text}")
                i += chunk_size - chunk_overlap
                if i >= len(words):
                    break
                    
        return final_chunks
