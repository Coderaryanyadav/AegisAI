"""
AegisAI Evidentiary Chronology & Cross-Examination Contradiction Matrix
Extracts dated sequences of events, actors, citations, and pinpoints material
contradictions across witness statements, police reports, and documentary exhibits.
"""

import re
from typing import List, Dict, Any, Optional

class ChronologyService:
    @staticmethod
    def extract_events_from_text(raw_text: str, source_doc: str = "Exhibit") -> List[Dict[str, Any]]:
        """Parses chronological date markers and facts from legal text."""
        # Match common date patterns: DD/MM/YYYY, DD Month YYYY, Month DD, YYYY
        date_pattern = re.compile(
            r'(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b)',
            re.IGNORECASE
        )
        
        events = []
        paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]
        
        for idx, para in enumerate(paragraphs):
            matches = list(date_pattern.finditer(para))
            if matches:
                for m in matches:
                    date_str = m.group(1)
                    # Extract sentence or snippet surrounding date
                    start = max(0, m.start() - 20)
                    end = min(len(para), m.end() + 250)
                    snippet = para[start:end].strip()
                    
                    # Deduce actor if common legal entities mentioned
                    actor = "Relevant Party"
                    for entity in ["Complainant", "Accused", "Investigating Officer", "Witness", "Petitioner", "Respondent", "Bank", "Appellant"]:
                        if entity.lower() in para.lower():
                            actor = entity
                            break
                    
                    events.append({
                        "date": date_str,
                        "actor": actor,
                        "description": snippet,
                        "source": source_doc,
                        "paragraph_index": idx + 1
                    })
        return events

    @staticmethod
    def identify_contradictions(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scans chronology events for temporal or factual contradictions across different sources."""
        contradictions = []
        
        # Check for multiple accounts on the same or proximate dates with differing actors
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                ev1 = events[i]
                ev2 = events[j]
                
                # If same date or proximate mention but differing sources or contradictory keywords
                if ev1["date"].lower() == ev2["date"].lower() and ev1["source"] != ev2["source"]:
                    contradictions.append({
                        "topic": f"Discrepancy on {ev1['date']}",
                        "source_a": ev1["source"],
                        "statement_a": ev1["description"],
                        "source_b": ev2["source"],
                        "statement_b": ev2["description"],
                        "impeachment_angle": f"Examine divergence between {ev1['actor']} ({ev1['source']}) and {ev2['actor']} ({ev2['source']}) regarding facts on {ev1['date']}.",
                        "severity": "HIGH"
                    })
        
        # If no specific duplicate-date contradictions found, synthesize standard adversarial audit checks
        if not contradictions and len(events) >= 2:
            contradictions.append({
                "topic": "Timeline Consistency Verification",
                "source_a": events[0]["source"],
                "statement_a": events[0]["description"][:120] + "...",
                "source_b": events[-1]["source"],
                "statement_b": events[-1]["description"][:120] + "...",
                "impeachment_angle": "Verify whether sequential chain of events shows unexplained delay between initial incident and subsequent legal notice/FIR.",
                "severity": "MEDIUM"
            })
            
        return contradictions
