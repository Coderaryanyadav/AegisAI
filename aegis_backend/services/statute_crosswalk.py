"""
AegisAI Dual-Statute Sanhitas Cross-Walker Service
Bidirectional concordance and comparative analysis between:
- Indian Penal Code (IPC 1860) <-> Bharatiya Nyaya Sanhita (BNS 2023)
- Code of Criminal Procedure (CrPC 1973) <-> Bharatiya Nagarik Suraksha Sanhita (BNSS 2023)
- Indian Evidence Act (IEA 1872) <-> Bharatiya Sakshya Adhiniyam (BSA 2023)
"""

from typing import List, Dict, Any, Optional

CROSSWALK_DATABASE: List[Dict[str, Any]] = [
    # --- IPC <-> BNS ---
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "302",
        "old_title": "Punishment for Murder",
        "new_act": "BNS",
        "new_section": "103(1)",
        "new_title": "Punishment for Murder",
        "substantive_delta": "Section 103(2) newly introduces death penalty or life imprisonment plus mandatory fine for mob lynching / murder by a group of five or more persons on grounds of race, caste, community, sex, or place of birth.",
        "precedent_status": "Applicable",
        "applicability_note": "Landmark tests for murder vs culpable homicide (Bachan Singh 'rarest of rare' doctrine; Machhi Singh) fully remain binding jurisprudence under BNS 103."
    },
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "307",
        "old_title": "Attempt to Murder",
        "new_act": "BNS",
        "new_section": "109",
        "new_title": "Attempt to Murder",
        "substantive_delta": "Penal structure retained. Clarifies infliction of hurt during the attempt attracts imprisonment for life or up to 10 years and fine.",
        "precedent_status": "Applicable",
        "applicability_note": "Intention and knowledge principles under State of Maharashtra v. Balram Bama Patil remain intact."
    },
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "420",
        "old_title": "Cheating and dishonestly inducing delivery of property",
        "new_act": "BNS",
        "new_section": "318(4)",
        "new_title": "Cheating and dishonestly inducing delivery of property",
        "substantive_delta": "Consolidated under general Cheating (Section 318). Imprisonment up to 7 years and fine retained. Modern digital fraudulent inducement explicitly covered under explanation.",
        "precedent_status": "Applicable",
        "applicability_note": "Requirement of fraudulent or dishonest intention at the inception of the transaction (Hridaya Ranjan Prasad Verma v. State of Bihar) continues to govern quashing petitions."
    },
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "376",
        "old_title": "Punishment for Rape",
        "new_act": "BNS",
        "new_section": "64",
        "new_title": "Punishment for Rape",
        "substantive_delta": "Minimum sentence remains 10 years extendable to life. Section 69 introduces a distinct offense for sexual intercourse by deceitful means or false promise of employment/promotion/marriage.",
        "precedent_status": "Modified",
        "applicability_note": "Distinction between breach of promise to marry and false promise at inception (Pramod Suryabhan Pawar v. State of Maharashtra) now statutorily codified under Section 69."
    },
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "406",
        "old_title": "Punishment for criminal breach of trust",
        "new_act": "BNS",
        "new_section": "316(2)",
        "new_title": "Punishment for criminal breach of trust",
        "substantive_delta": "Maximum punishment increased from 3 years to 5 years imprisonment or fine or both.",
        "precedent_status": "Applicable",
        "applicability_note": "Ingredients of entrustment and dishonest misappropriation under Jaswantrai Manilal Akhaney v. State of Bombay apply directly."
    },
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "498A",
        "old_title": "Husband or relative of husband subjecting woman to cruelty",
        "new_act": "BNS",
        "new_section": "85 / 86",
        "new_title": "Husband or relative of husband of a woman subjecting her to cruelty",
        "substantive_delta": "Cruelty definition bifurcated into Section 85 (penal clause up to 3 years) and Section 86 (detailed statutory definitions of mental and physical cruelty).",
        "precedent_status": "Applicable",
        "applicability_note": "Arnesh Kumar v. State of Bihar guidelines on non-automatic arrest for offenses punishable under 7 years apply vigorously."
    },
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "124A",
        "old_title": "Sedition",
        "new_act": "BNS",
        "new_section": "152",
        "new_title": "Act endangering sovereignty, unity and integrity of India",
        "substantive_delta": "The colonial term 'Sedition' (Rajdroh) was omitted; replaced with Deshdroh / acts inciting secession, armed rebellion, or subversive activities. Minimum sentence increased from 3 years to 7 years.",
        "precedent_status": "Modified",
        "applicability_note": "S.G. Vombatkere stay and Kedar Nath Singh requirements of incitement to imminent public disorder are being adapted to Section 152."
    },
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "304B",
        "old_title": "Dowry Death",
        "new_act": "BNS",
        "new_section": "80",
        "new_title": "Dowry Death",
        "substantive_delta": "Substance and 7-year minimum up to life sentence retained.",
        "precedent_status": "Applicable",
        "applicability_note": "Satbir Singh v. State of Haryana regarding 'soon before death' proximate test remains completely valid."
    },
    {
        "category": "Substantive Criminal Law",
        "old_act": "IPC",
        "old_section": "34",
        "old_title": "Acts done by several persons in furtherance of common intention",
        "new_act": "BNS",
        "new_section": "3(5)",
        "new_title": "Joint liability / Common Intention",
        "substantive_delta": "Relocated into General Explanations under Section 3(5). Core joint liability rule unchanged.",
        "precedent_status": "Applicable",
        "applicability_note": "Prior meeting of minds (Pandurang v. State of Hyderabad) continues to govern vicarious criminal liability."
    },

    # --- CrPC <-> BNSS ---
    {
        "category": "Criminal Procedure",
        "old_act": "CrPC",
        "old_section": "154",
        "old_title": "Information in cognizable cases (FIR)",
        "new_act": "BNSS",
        "new_section": "173",
        "new_title": "Information in cognizable cases (Zero FIR & e-FIR)",
        "substantive_delta": "Statutorily mandates 'Zero FIR' regardless of jurisdictional boundaries. Expressly permits 'e-FIR' (electronic FIR), requiring informant signature within 3 days.",
        "precedent_status": "Applicable",
        "applicability_note": "Lalita Kumari v. Govt of UP mandatory FIR registration principles codified directly into Section 173(3) with a preliminary inquiry window of 14 days for offenses punishable between 3-7 years."
    },
    {
        "category": "Criminal Procedure",
        "old_act": "CrPC",
        "old_section": "167",
        "old_title": "Procedure when investigation cannot be completed in twenty-four hours (Police Custody)",
        "new_act": "BNSS",
        "new_section": "187",
        "new_title": "Procedure when investigation cannot be completed in twenty-four hours",
        "substantive_delta": "Permits 15 days police custody in whole or in parts throughout the initial 40 days (for 60-day investigations) or 60 days (for 90-day investigations), altering the earlier strict first-15-days-only rule under CBI v. Anupam Kulkarni.",
        "precedent_status": "Modified",
        "applicability_note": "V. Senthil Balaji v. State clarification on police custody staggered windows now codified in BNSS 187."
    },
    {
        "category": "Criminal Procedure",
        "old_act": "CrPC",
        "old_section": "437",
        "old_title": "When bail may be taken in case of non-bailable offence",
        "new_act": "BNSS",
        "new_section": "480",
        "new_title": "When bail may be taken in case of non-bailable offence",
        "substantive_delta": "Adds progressive relief for first-time undertrial offenders (Section 479) allowing bond release upon completing 1/3rd of the maximum term instead of 1/2.",
        "precedent_status": "Applicable",
        "applicability_note": "Satender Kumar Antil v. CBI guidelines on bail classification and liberty safeguards remain paramount."
    },
    {
        "category": "Criminal Procedure",
        "old_act": "CrPC",
        "old_section": "438",
        "old_title": "Direction for grant of bail to person apprehending arrest (Anticipatory Bail)",
        "new_act": "BNSS",
        "new_section": "482",
        "new_title": "Direction for grant of bail to person apprehending arrest",
        "substantive_delta": "Provisions largely preserved with explicit guidelines on conditions and restrictions.",
        "precedent_status": "Applicable",
        "applicability_note": "Sushila Aggarwal v. State (NCT of Delhi) ruling that anticipatory bail should not be routinely time-limited remains operative."
    },
    {
        "category": "Criminal Procedure",
        "old_act": "CrPC",
        "old_section": "439",
        "old_title": "Special powers of High Court or Court of Session regarding bail",
        "new_act": "BNSS",
        "new_section": "483",
        "new_title": "Special powers of High Court or Court of Session regarding bail",
        "substantive_delta": "Notice to public prosecutor and informant presence in POCSO/serious sexual offense bail hearings reaffirmed.",
        "precedent_status": "Applicable",
        "applicability_note": "P. Chidambaram v. Directorate of Enforcement triple test (flight risk, witness tampering, evidence destruction) continues to dictate regular bail hearings."
    },
    {
        "category": "Criminal Procedure",
        "old_act": "CrPC",
        "old_section": "482",
        "old_title": "Saving of inherent powers of High Court",
        "new_act": "BNSS",
        "new_section": "528",
        "new_title": "Saving of inherent powers of High Court",
        "substantive_delta": "Exact inherent jurisdiction for preventing abuse of process and securing ends of justice retained verbatim under Section 528.",
        "precedent_status": "Applicable",
        "applicability_note": "State of Haryana v. Bhajan Lal 7-point quashing parameters and Gian Singh compromise quashing remain 100% good law."
    },
    {
        "category": "Criminal Procedure",
        "old_act": "CrPC",
        "old_section": "41A",
        "old_title": "Notice of appearance before police officer",
        "new_act": "BNSS",
        "new_section": "35(3)",
        "new_title": "Notice of appearance before police officer",
        "substantive_delta": "Mandatory prior approval from DSP/Assistant Commissioner rank before arresting elderly (>60 yrs) or infirm persons for offenses <3 yrs.",
        "precedent_status": "Applicable",
        "applicability_note": "Arnesh Kumar v. State of Bihar checklist requirement applies squarely to Section 35(3)."
    },

    # --- IEA <-> BSA ---
    {
        "category": "Law of Evidence",
        "old_act": "IEA",
        "old_section": "65B",
        "old_title": "Admissibility of electronic records",
        "new_act": "BSA",
        "new_section": "63",
        "new_title": "Admissibility of electronic records",
        "substantive_delta": "Electronic/digital records elevated as primary evidence under Section 57. Section 63 introduces a standardized statutory certificate format in the Schedule (Part A & Part B), modernizing cloud storage, hash values, and server metadata admissibility.",
        "precedent_status": "Applicable",
        "applicability_note": "Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal certificate requirement remains mandatory, now streamlined under the statutory Schedule form."
    },
    {
        "category": "Law of Evidence",
        "old_act": "IEA",
        "old_section": "27",
        "old_title": "How much of information received from accused may be proved (Recovery Memo)",
        "new_act": "BSA",
        "new_section": "23(2)",
        "new_title": "Discovery of fact pursuant to confession to police",
        "substantive_delta": "Proviso to Section 23 incorporates discovery rule. Requires video recording/panchnama documentation where feasible.",
        "precedent_status": "Applicable",
        "applicability_note": "Pulukuri Kotayya v. King Emperor and Subramanya v. State of Karnataka recovery principles remain foundational."
    },
    {
        "category": "Law of Evidence",
        "old_act": "IEA",
        "old_section": "32(1)",
        "old_title": "Cases in which statement of relevant fact by person who is dead is relevant (Dying Declaration)",
        "new_act": "BSA",
        "new_section": "26(a)",
        "new_title": "Statements by person who cannot be called as witness (Dying Declaration)",
        "substantive_delta": "Retains dying declaration principles. Encourages contemporaneous audio-video recording by magistrates.",
        "precedent_status": "Applicable",
        "applicability_note": "Atbir v. Govt of NCT of Delhi 10-point dying declaration guidelines apply directly."
    }
]

class StatuteCrosswalkService:
    @staticmethod
    def search(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search crosswalk database across old section, new section, titles, and deltas."""
        q = query.strip().lower()
        results = []
        for item in CROSSWALK_DATABASE:
            if category and category.lower() not in item["category"].lower():
                continue
            
            # Match query against section numbers, acts, or text
            match = (
                q in item["old_section"].lower() or
                q in item["new_section"].lower() or
                q in item["old_act"].lower() or
                q in item["new_act"].lower() or
                q in item["old_title"].lower() or
                q in item["new_title"].lower() or
                q in item["substantive_delta"].lower() or
                q in item["applicability_note"].lower()
            )
            if match or not q:
                results.append(item)
        return results

    @staticmethod
    def get_by_section(act: str, section: str) -> Optional[Dict[str, Any]]:
        act_clean = act.strip().upper()
        sec_clean = section.strip().lower()
        for item in CROSSWALK_DATABASE:
            if act_clean in ("IPC", "CRPC", "IEA") and item["old_act"].upper() == act_clean:
                if sec_clean in item["old_section"].lower():
                    return item
            elif act_clean in ("BNS", "BNSS", "BSA") and item["new_act"].upper() == act_clean:
                if sec_clean in item["new_section"].lower():
                    return item
        return None
