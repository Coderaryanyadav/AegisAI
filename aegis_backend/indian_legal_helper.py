import re
from typing import Dict, Any, Optional

# Standard citation normalization regexes
SC_CITATION_PATTERNS = [
    r"(?P<year>\d{4})\s*\((?P<reporter>SCC|SCR|SCC\s*\(Cri\))\)\s*(?P<volume>\d+)\s*(?P<page>\d+)",
    r"AIR\s*(?P<year>\d{4})\s*SC\s*(?P<page>\d+)",
    r"(?P<year>\d{4})\s*INSC\s*(?P<page>\d+)"
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

        if "IPC" in act_upper:
            return cls.IPC_TO_BNS_MAP.get(sec_clean)
        elif "CRPC" in act_upper:
            return cls.CRPC_TO_BNSS_MAP.get(sec_clean)
        elif "IEA" in act_upper or "EVIDENCE" in act_upper:
            return cls.IEA_TO_BSA_MAP.get(sec_clean)
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
