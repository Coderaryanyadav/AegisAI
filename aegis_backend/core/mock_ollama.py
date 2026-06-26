import os
import re
import json

def get_mock_completion(prompt: str, system_prompt: str = None, json_mode: bool = False) -> str:
    """Heuristic test fallbacks used for development and local testing when Ollama is offline."""
    # Find snippet
    snippet = ""
    for marker in ["Document Snippet:\n", "Contract Snippet:\n", "Context Details:\n"]:
        if marker in prompt:
            parts = prompt.split(marker)
            if len(parts) > 1:
                snippet = parts[1].split("\n\n")[0].strip()
                break
    
    # If no snippet marker found, default to prompt content
    if not snippet:
        snippet = prompt

    if json_mode:
        prompt_lower = prompt.lower()
        sys_lower = (system_prompt or "").lower()
        
        # Check for specific JSON templates requested
        if "timeline" in prompt_lower or "timeline" in sys_lower:
            sentences = re.split(r'(?<=[.!?])\s+', snippet)
            items = []
            for sent in sentences:
                sent_clean = sent.strip()
                if not sent_clean:
                    continue
                year_match = re.search(r'\b(?:19|20)\d{2}\b', sent_clean)
                if year_match:
                    date_str = year_match.group(0)
                    clean_date = re.search(r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s+(?:19|20)\d{2}\b', sent_clean, re.IGNORECASE)
                    if clean_date:
                        date_str = clean_date.group(0)
                    
                    parties = re.findall(r'\b[A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*\b', sent_clean)
                    parties_clean = [p for p in parties if p.lower() not in ["lease", "agreement", "deed", "section", "act", "the", "under", "court", "judgment", "jurisdiction", "date", "contract", "parties", "party", "annexure", "schedule"]]
                    
                    items.append({
                        "date": date_str,
                        "event": sent_clean,
                        "involved_parties": list(set(parties_clean))[:3]
                    })
            
            if not items:
                items = [
                    {"date": "2026-01-10", "event": "Tata executed contract", "involved_parties": ["Tata"]},
                    {"date": "2026-02-12", "event": "Adani breached it", "involved_parties": ["Adani"]},
                    {"date": "2026-03-01", "event": "Arbitration notices were sent", "involved_parties": ["Tata", "Adani"]}
                ]
            return json.dumps(items)
            
        elif "risk" in prompt_lower or "risk" in sys_lower or "scan" in prompt_lower:
            sentences = re.split(r'(?<=[.!?])\s+', snippet)
            risks = []
            keywords = ["liable", "liability", "termination", "terminate", "indemnify", "indemnity", "risk", "breach", "governing law", "jurisdiction", "warrant", "warranty"]
            for sent in sentences:
                sent_clean = sent.strip()
                if not sent_clean:
                    continue
                for kw in keywords:
                    if kw in sent_clean.lower():
                        if kw in ["liable", "liability", "breach", "indemnify"]:
                            rating = "High"
                            advice = "Review liability limitations and indemnity exposure caps."
                            title = f"Liability / Indemnity Risk: {kw.capitalize()}"
                        elif kw in ["terminate", "termination", "jurisdiction", "governing law"]:
                            rating = "Medium"
                            advice = "Ensure reciprocal terms and mutually convenient dispute resolution venue."
                            title = f"Contract Operations Risk: {kw.capitalize()}"
                        else:
                            rating = "Low"
                            advice = "Verify standard warranty and compliance language."
                            title = f"General Risk Factor: {kw.capitalize()}"
                        
                        risks.append({
                            "clause_title": title,
                            "risk_rating": rating,
                            "summary": sent_clean,
                            "remediation_advice": advice
                        })
                        break
            
            if not risks:
                risks = [
                    {"clause_title": "Limitation of Liability Waiver", 
                     "risk_rating": "High", 
                     "summary": "The lessor shall not be held liable for any building structural failure or collapses.", 
                     "remediation_advice": "Request deletion of safety liability exemptions."}
                ]
            return json.dumps(risks)
            
        elif "bns" in prompt_lower or "ipc" in prompt_lower:
            sec_match = re.search(r'\b\d+\b', prompt)
            sec = sec_match.group(0) if sec_match else "378"
            from aegis_backend.indian_legal_helper import IndianLegalHelper
            mapping = IndianLegalHelper.convert_section("IPC", sec)
            if mapping:
                return json.dumps({
                    "bns_section": mapping["new_section"],
                    "title": mapping["subject"],
                    "description": mapping["description"]
                })
            else:
                return json.dumps({
                    "bns_section": "N/A", 
                    "title": "Unmapped Act Section",
                    "description": f"Section {sec} was not found in the offline conversion database."
                })
                
        elif "normalize" in prompt_lower or "citation" in prompt_lower:
            from aegis_backend.indian_legal_helper import IndianLegalHelper
            citation = "2024 SCC DEL 105"
            cit_match = re.search(r'\b\d{4}\s*[A-Z\s\(\)]+\s*\d+\b', prompt)
            if cit_match:
                citation = cit_match.group(0)
            norm = IndianLegalHelper.normalize_citation(citation)
            return json.dumps({
                "normalized": norm or citation
            })
            
        elif "draft" in prompt_lower or "template" in prompt_lower or "generate" in prompt_lower:
            client_name = "Tata Energy"
            debtor_name = "Adani Transmission"
            amount = "500000"
            
            client_match = re.search(r'client_name:\s*([^\n,]+)', prompt, re.IGNORECASE)
            if client_match:
                client_name = client_match.group(1).strip()
            debtor_match = re.search(r'debtor_name:\s*([^\n,]+)', prompt, re.IGNORECASE)
            if debtor_match:
                debtor_name = debtor_match.group(1).strip()
            amount_match = re.search(r'amount_due:\s*([^\n,]+)', prompt, re.IGNORECASE)
            if amount_match:
                amount = amount_match.group(1).strip()
                
            return json.dumps({
                "draft": f"LEGAL NOTICE DEMAND\n\nTo:\n{debtor_name}\n\nWe act on behalf of our client, {client_name}. This is a formal demand notice for the unpaid sum of INR {amount}. Please clear the balance immediately to avoid litigation."
            })
            
        elif "outcome" in prompt_lower:
            return json.dumps({
                "outcome": "Offline Heuristic Prediction: Favorable outcome anticipated based on the absence of explicit penalty clauses in matching extracted context.",
                "confidence": "0.78"
            })
        elif "simplify" in prompt_lower:
            first_sentence = snippet.split(".")[0].strip() if snippet else "The clause is simplified."
            return json.dumps({
                "simplified": f"Simplified Summary: {first_sentence}."
            })
        else:
            return json.dumps({
                "response": "AegisAI Offline heuristic answer",
                "status": "offline_fallback"
            })
    else:
        context_match = re.search(r'Context Details:\n(.*?)\nQuery:', prompt, re.DOTALL)
        query_match = re.search(r'Query:\s*(.*?)\n', prompt)
        
        context_str = context_match.group(1).strip() if context_match else ""
        query_str = query_match.group(1).strip() if query_match else ""
        
        if context_str and query_str:
            query_words = [w.lower() for w in query_str.split() if len(w) > 3]
            sentences = re.split(r'(?<=[.!?])\s+', context_str)
            matching_sentences = []
            for sent in sentences:
                sent_clean = sent.strip()
                if not sent_clean:
                    continue
                for qw in query_words:
                    if qw in sent_clean.lower():
                        matching_sentences.append(f"> {sent_clean}")
                        break
                        
            if matching_sentences:
                passages = "\n\n".join(matching_sentences[:3])
                return (
                    f"AegisAI Offline RAG Search Result:\n\n"
                    f"The local AI model is currently offline/loading. Below are matching passages from the case documents relating to your query:\n\n"
                    f"{passages}"
                )
            else:
                snippet_text = "\n\n".join([f"> {s.strip()}" for s in sentences[:2] if s.strip()])
                return (
                    f"AegisAI Offline RAG Search Result:\n\n"
                    f"The local AI model is currently offline/loading. The relevant context from the case file reads:\n\n"
                    f"{snippet_text}"
                )
        
        return (
            "AegisAI Offline Assistant: Local AI model is currently offline or loading. "
            "Please ensure Ollama is active to enable full generative model reasoning."
        )
