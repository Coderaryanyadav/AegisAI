import re
import os
import json
from typing import Dict, Any, Optional, List

# Standard citation normalization regexes
SC_CITATION_PATTERNS = [
    r"(?P<year>\d{4})\s*\((?P<reporter>SCC|SCR|SCC\s*\(Cri\))\)\s*(?P<volume>\d+)\s*(?P<page>\d+)",
    r"AIR\s*(?P<year>\d{4})\s*SC\s*(?P<page>\d+)",
    r"(?P<year>\d{4})\s*INSC\s*(?P<page>\d+)"
]

ACT_ALIASES = {
    "IPC": "IPC",
    "INDIAN PENAL CODE": "IPC",
    "I.P.C": "IPC",
    "I P C": "IPC",
    "BNS": "BNS",
    "BHARATIYA NYAYA SANHITA": "BNS",
    "CRPC": "CRPC",
    "CR.P.C": "CRPC",
    "CODE OF CRIMINAL PROCEDURE": "CRPC",
    "BNSS": "BNSS",
    "BHARATIYA NAGARIK SURAKSHA SANHITA": "BNSS",
    "IEA": "IEA",
    "INDIAN EVIDENCE ACT": "IEA",
    "EVIDENCE ACT": "IEA",
    "BSA": "BSA",
    "BHARATIYA SAKSHYA ADHINIYAM": "BSA",
}

STATUTORY_CITATION_PATTERNS = [
    r"(?P<act>IPC|Indian Penal Code|I\.?\s*P\.?\s*C\.?|BNS|Bharatiya Nyaya Sanhita|CrPC|Cr\.?\s*P\.?\s*C\.?|Code of Criminal Procedure|BNSS|Bharatiya Nagarik Suraksha Sanhita|IEA|Indian Evidence Act|Evidence Act|BSA|Bharatiya Sakshya Adhiniyam)[^\n]{0,40}?(?:Section|Sec\.?|S\.?)\s*(?P<section>\d+[A-Za-z]?(?:\(\d+\))?)",
    r"(?:Section|Sec\.?|S\.?)\s*(?P<section2>\d+[A-Za-z]?(?:\(\d+\))?)\s*(?:of\s*(?:the\s*)?)?(?P<act2>IPC|Indian Penal Code|I\.?\s*P\.?\s*C\.?|BNS|CrPC|Cr\.?\s*P\.?\s*C\.?|BNSS|IEA|Indian Evidence Act|Evidence Act|BSA)",
    r"(?P<act3>IPC|BNS|CrPC|BNSS|IEA|BSA)\s*(?:Section|Sec\.?|S\.?)\s*(?P<section3>\d+[A-Za-z]?(?:\(\d+\))?)",
]

class IndianLegalHelper:
    """Offline cross-referencing converter for new Indian Laws (2024) and Citation normalizer."""
    
    # IPC to BNS mapping (Bharatiya Nyaya Sanhita, 2023)
    IPC_TO_BNS_MAP = {
        "302": {
            "new_section": "101",
            "act": "BNS",
            "subject": "Punishment for Murder",
            "change_type": "Modified numbering",
            "description": "Murder, previously under Section 302 of the IPC, is now defined under Section 101 of the BNS. Provisions for death penalty or life imprisonment remain, but structure is updated."
        },
        "307": {
            "new_section": "109",
            "act": "BNS",
            "subject": "Attempt to Murder",
            "change_type": "Modified numbering",
            "description": "Attempt to murder is shifted from Section 307 of the IPC to Section 109 of the BNS."
        },
        "375": {
            "new_section": "63",
            "act": "BNS",
            "subject": "Definition of Rape",
            "change_type": "Restructured",
            "description": "Rape definition shifts from Section 375 of the IPC to Section 63 of the BNS. Consent age and exceptions remain broadly similar but restructured under offences against women and children."
        },
        "376": {
            "new_section": "64",
            "act": "BNS",
            "subject": "Punishment for Rape",
            "change_type": "Restructured",
            "description": "Punishment for rape shifts from Section 376 of the IPC to Section 64 of the BNS. Minimum sentence increased in various categories."
        },
        "378": {
            "new_section": "303",
            "act": "BNS",
            "subject": "Theft",
            "change_type": "Modified numbering",
            "description": "Theft is defined under Section 303 of the BNS (previously Section 378 of the IPC)."
        },
        "379": {
            "new_section": "303(2)",
            "act": "BNS",
            "subject": "Punishment for Theft",
            "change_type": "Modified with community service",
            "description": "Shifts to Section 303(2) of the BNS. Adds community service as an alternative punishment for first-time offenders where stolen value is less than Rs. 5,000."
        },
        "420": {
            "new_section": "318",
            "act": "BNS",
            "subject": "Cheating and dishonestly inducing delivery of property",
            "change_type": "Modified numbering",
            "description": "Cheating shifts from Section 420 of the IPC to Section 318 of the BNS."
        },
        "124A": {
            "new_section": "152",
            "act": "BNS",
            "subject": "Act endangering sovereignty, unity and integrity of India",
            "change_type": "Replaced & Redefined",
            "description": "Sedition (IPC 124A) is repealed. Replaced by Section 152 of the BNS, which penalizes acts endangering sovereignty, unity, and integrity of India, explicitly excluding word 'sedition' but expanding electronic/financial facilitation scopes."
        },
        "141": {
            "new_section": "189",
            "act": "BNS",
            "subject": "Unlawful Assembly",
            "change_type": "Modified numbering",
            "description": "Shifts to Section 189 of the BNS."
        },
        "499": {
            "new_section": "356",
            "act": "BNS",
            "subject": "Defamation",
            "change_type": "Modified with community service option",
            "description": "Defamation shifts to Section 356 of the BNS. Includes a provision for community service as a punishment option instead of jail/fine."
        }
    }

    # CrPC to BNSS mapping (Bharatiya Nagarik Suraksha Sanhita, 2023)
    CRPC_TO_BNSS_MAP = {
        "154": {
            "new_section": "173",
            "act": "BNSS",
            "subject": "Information in cognizable cases (FIR)",
            "change_type": "Modified (Zero FIR legislated)",
            "description": "FIR registration shifts to Section 173 of the BNSS. Formally codifies Zero FIR (allowing registration at any police station regardless of jurisdiction) and electronic FIR filings."
        },
        "161": {
            "new_section": "180",
            "act": "BNSS",
            "subject": "Examination of witnesses by police",
            "change_type": "Expanded (Electronic recordings)",
            "description": "Witness examinations shift to Section 180 of the BNSS. Formally authorizes audio-video recording of witness statements via electronic means."
        },
        "167": {
            "new_section": "187",
            "act": "BNSS",
            "subject": "Procedure when investigation cannot be completed in 24 hours",
            "change_type": "Expanded police custody window",
            "description": "Shifts to Section 187 of the BNSS. Allows police custody of 15 days to be split across the first 40 or 60 days of detention, rather than requiring it all in the first 15 days."
        },
        "438": {
            "new_section": "482",
            "act": "BNSS",
            "subject": "Direction for grant of bail to person apprehending arrest (Anticipatory Bail)",
            "change_type": "Modified numbering",
            "description": "Anticipatory bail shifts to Section 482 of the BNSS."
        },
        "482": {
            "new_section": "528",
            "act": "BNSS",
            "subject": "Saving of inherent powers of High Court",
            "change_type": "Modified numbering",
            "description": "High Court inherent powers shift to Section 528 of the BNSS."
        }
    }

    # Evidence Act to BSA mapping (Bharatiya Sakshya Adhiniyam, 2023)
    IEA_TO_BSA_MAP = {
        "3": {
            "new_section": "2",
            "act": "BSA",
            "subject": "Interpretation clause (Document definition)",
            "change_type": "Expanded electronic scopes",
            "description": "Shifts to Section 2 of the BSA. The definition of a 'Document' is expanded to explicitly include electronic or digital records, emails, server logs, smartphone messages, and locations."
        },
        "65B": {
            "new_section": "63",
            "act": "BSA",
            "subject": "Admissibility of electronic records certificate",
            "change_type": "Restructured certificate requirements",
            "description": "Secondary electronic evidence admissibility shifts to Section 63 of the BSA. Updates certificate guidelines to streamline presentation of digital devices and network drives."
        }
    }

    @classmethod
    def convert_section(cls, act: str, section: str) -> Optional[Dict[str, Any]]:
        """Converts old IPC/CrPC/IEA sections to new BNS/BNSS/BSA sections."""
        act_upper = act.upper().strip()
        sec_clean = section.strip()

        # 1. First attempt database lookup using sync session
        try:
            from aegis_backend.database import SessionLocal, StatutoryMapping
            db = SessionLocal()
            try:
                mapping = db.query(StatutoryMapping).filter(
                    StatutoryMapping.old_act.ilike(act_upper),
                    StatutoryMapping.old_section == sec_clean
                ).first()
                if mapping:
                    return {
                        "new_section": mapping.new_section,
                        "act": mapping.new_act,
                        "subject": mapping.subject,
                        "change_type": mapping.change_type,
                        "description": mapping.description
                    }
            finally:
                db.close()
        except Exception:
            pass

        # 2. Fallback to JSON or static configs if database query is empty or fails
        ipc_map = cls.IPC_TO_BNS_MAP
        crpc_map = cls.CRPC_TO_BNSS_MAP
        iea_map = cls.IEA_TO_BSA_MAP

        try:
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(curr_dir, "legal_mappings.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ipc_map = data.get("IPC_TO_BNS_MAP", ipc_map)
                    crpc_map = data.get("CRPC_TO_BNSS_MAP", crpc_map)
                    iea_map = data.get("IEA_TO_BSA_MAP", iea_map)
        except Exception:
            pass

        if "IPC" in act_upper:
            return ipc_map.get(sec_clean)
        elif "CRPC" in act_upper:
            return crpc_map.get(sec_clean)
        elif "IEA" in act_upper or "EVIDENCE" in act_upper:
            return iea_map.get(sec_clean)
        return None

    @classmethod
    def normalize_citation(cls, citation: str) -> str:
        """
        Normalizes various Indian legal citation formats to enable exact matching.
        E.g. "AIR 1996 SC 1234" -> "1996-air-sc-1234"
             "2024 INSC 15" -> "2024-insc-15"
        """
        clean = citation.strip().upper()
        # Remove parentheses, commas, dots
        clean = re.sub(r"[\(\),\.]", " ", clean)
        # Squeeze spaces
        clean = re.sub(r"\s+", " ", clean).strip()

        for pattern in SC_CITATION_PATTERNS:
            match = re.search(pattern, clean, re.IGNORECASE)
            if match:
                group_dict = match.groupdict()
                year = group_dict.get("year", "")
                page = group_dict.get("page", "")
                reporter = group_dict.get("reporter", "SC").strip().lower().replace(" ", "")
                vol = group_dict.get("volume", "")
                
                if vol:
                    return f"{year}-{vol}-{reporter}-{page}"
                return f"{year}-{reporter}-{page}"

        # General fallback normalization
        fallback = clean.lower().replace(" ", "-")
        return fallback

    @classmethod
    def _normalize_act_name(cls, act_raw: str) -> str:
        cleaned = re.sub(r"[\.\s]+", " ", act_raw.strip().upper())
        return ACT_ALIASES.get(cleaned, cleaned.split()[0] if cleaned else act_raw.upper())

    @classmethod
    def detect_statutory_citations(cls, text: str) -> List[Dict[str, Any]]:
        """
        Detect statutory citations in legal text (e.g. 'IPC Section 302', 'S. 154 CrPC').
        Returns deduplicated list of citation objects with act, section, and matched text span.
        """
        if not text or not text.strip():
            return []

        seen = set()
        citations: List[Dict[str, Any]] = []

        for pattern in STATUTORY_CITATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groupdict()
                act_raw = groups.get("act") or groups.get("act2") or groups.get("act3") or ""
                section = groups.get("section") or groups.get("section2") or groups.get("section3") or ""
                if not act_raw or not section:
                    continue

                act = cls._normalize_act_name(act_raw)
                section_clean = section.strip().upper()
                key = (act, section_clean)
                if key in seen:
                    continue
                seen.add(key)

                mapping = cls.convert_section(act.lower(), section_clean)
                citations.append({
                    "act": act,
                    "section": section_clean,
                    "matched_text": match.group(0).strip(),
                    "start": match.start(),
                    "end": match.end(),
                    "mapping": mapping,
                })

        citations.sort(key=lambda c: c["start"])
        return citations

    @classmethod
    def resolve_bare_act_lookup(cls, act: str, section: str) -> Optional[Dict[str, Any]]:
        """Resolve a statutory reference to its mapped equivalent and lookup metadata."""
        act_upper = cls._normalize_act_name(act)
        section_clean = section.strip()

        mapping = cls.convert_section(act.lower(), section_clean)
        target_act = mapping["act"] if mapping else act_upper
        target_section = mapping["new_section"] if mapping else section_clean

        return {
            "requested_act": act_upper,
            "requested_section": section_clean,
            "target_act": target_act,
            "target_section": target_section,
            "mapping": mapping,
        }
