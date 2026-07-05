import os
import json
import uuid
import shutil
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from aegis_backend.database import get_db, get_db_ro, User
from aegis_backend.schemas.models import (
    ResearchQuery, ConflictCheckRequest, FormatDraftRequest, SimplifyClauseRequest,
    FIRAnalysisRequest, PredictOutcomeRequest, VoiceTranscribeRequest
)
from aegis_backend.core.security import (
    get_current_user, verify_lawyer_or_admin, log_audit_trail, safe_db_rollback, check_prompt_injection
)
from aegis_backend.indian_legal_helper import IndianLegalHelper
from aegis_backend.ollama_service import OllamaService
from aegis_backend.services.research_service import ResearchService

router = APIRouter(tags=["research"])

@router.post("/research/query")
async def query_legal_rag(req: ResearchQuery, db: AsyncSession = Depends(get_db), db_ro: AsyncSession = Depends(get_db_ro), current_user: User = Depends(verify_lawyer_or_admin)):
    result = await ResearchService.query_legal_rag(db_ro, current_user, req)
    await log_audit_trail(db, current_user.email, "LEGAL_SEARCH", "rag", details=req.query)
    return result

@router.post("/research/query/stream")
async def query_legal_rag_stream(
    req: ResearchQuery,
    db: AsyncSession = Depends(get_db),
    db_ro: AsyncSession = Depends(get_db_ro),
    current_user: User = Depends(verify_lawyer_or_admin)
):
    if check_prompt_injection(req.query):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Potential prompt injection or instruction override attempt detected. Request blocked."
        )

    # Note: For streaming, we still use OllamaService directly to yield chunks to FastAPI, 
    # as the generator pattern is tightly coupled to the HTTP StreamingResponse.
    # To keep this clean, we'll implement it slightly inline here, but delegate caching checks.
    from aegis_backend.core.cache import rag_cache
    from aegis_backend.vector_store import vector_store

    sorted_ids = sorted(req.matter_ids or [])
    cache_key = f"{current_user.email}:{req.model_name}:{json.dumps(sorted_ids)}:{req.query}"
    cached = rag_cache.get(cache_key)

    async def sse_generator():
        if cached:
            await log_audit_trail(db, current_user.email, "LEGAL_SEARCH_CACHED", "rag", details=req.query)
            yield f"data: {json.dumps(cached)}\n\n"
            return

        chunks = vector_store.query_hybrid(req.query, limit=5, document_ids=req.matter_ids)
        prompt, system_prompt = ResearchService.build_rag_context_and_prompts(req.query, chunks)

        full_response_parts = []
        async for chunk in OllamaService.generate_completion_stream(
            model=req.model_name,
            prompt=prompt,
            system_prompt=system_prompt
        ):
            full_response_parts.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        full_text = "".join(full_response_parts)
        sources = [{"id": c["id"], "text": c["content"], "metadata": c["metadata"]} for c in chunks if not check_prompt_injection(c["content"])]
        result_data = {
            "response": full_text,
            "sources": sources,
            "disclaimer": "AI-generated content is for informational purposes only. It is not professional legal advice and must be independently verified by an advocate."
        }

        if full_text:
            rag_cache.set(cache_key, result_data)

        await log_audit_trail(db, current_user.email, "LEGAL_SEARCH", "rag", details=req.query)
        yield f"data: {json.dumps(result_data)}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@router.get("/helper/ipc-bns")
async def get_statutory_mapping(act: str, section: str, db_ro: AsyncSession = Depends(get_db_ro)):
    mapping = IndianLegalHelper.convert_section(act, section)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found for the requested section.")
    
    new_section = mapping.get("new_section")
    target_act = mapping.get("act")
    
    full_text = None
    if new_section and target_act:
        full_text = await ResearchService.get_statutory_mapping_text(db_ro, target_act, new_section)
            
    return {
        **mapping,
        "full_text": full_text
    }

@router.post("/helper/normalize-citation")
def normalize_citation(citation: str = Form(...)):
    normalized = IndianLegalHelper.normalize_citation(citation)
    return {"original": citation, "normalized": normalized}

@router.post("/helper/detect-citations")
async def detect_statutory_citations(
    text: str = Form(...),
    db_ro: AsyncSession = Depends(get_db_ro),
    current_user: User = Depends(get_current_user),
):
    citations = IndianLegalHelper.detect_statutory_citations(text)
    enriched = []
    for cite in citations:
        lookup = IndianLegalHelper.resolve_bare_act_lookup(cite["act"], cite["section"])
        full_text = None
        if lookup:
            full_text = await ResearchService.get_statutory_mapping_text(
                db_ro, lookup["target_act"], lookup["target_section"]
            )
        enriched.append({**cite, "lookup": lookup, "full_text": full_text})
    return {"citations": enriched, "count": len(enriched)}

@router.get("/helper/bare-act/{act}/{section}")
async def get_bare_act_section(
    act: str,
    section: str,
    db_ro: AsyncSession = Depends(get_db_ro),
    current_user: User = Depends(get_current_user),
):
    lookup = IndianLegalHelper.resolve_bare_act_lookup(act, section)
    if not lookup:
        raise HTTPException(status_code=404, detail="Statutory reference not found.")
    full_text = await ResearchService.get_statutory_mapping_text(
        db_ro, lookup["target_act"], lookup["target_section"]
    )
    if not full_text:
        raise HTTPException(status_code=404, detail="Bare Act section text not found in local library.")
    return {**lookup, "full_text": full_text}

@router.post("/analyze/cause-list")
async def parse_cause_list(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(verify_lawyer_or_admin)
):
    import tempfile
    import asyncio
    temp_pdf_path = os.path.join(tempfile.gettempdir(), f"cause_list_{uuid.uuid4()}.pdf")
    
    file_data = await file.read()
    
    def write_temp_file():
        with open(temp_pdf_path, "wb") as buffer:
            buffer.write(file_data)
            
    await asyncio.to_thread(write_temp_file)
        
    try:
        result = await ResearchService.process_cause_list(db, temp_pdf_path, file.filename)
        await log_audit_trail(db, current_user.email, "PARSE_CAUSE_LIST", "cause_list", details=f"Scanned {file.filename}, found {result['matches_found']} matches.")
        return result
    finally:
        def cleanup_temp_file():
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        await asyncio.to_thread(cleanup_temp_file)

@router.post("/analyze/extract-timeline")
async def extract_case_timeline(document_id: int, model_name: str = "mistral:latest", db_ro: AsyncSession = Depends(get_db_ro), current_user: User = Depends(verify_lawyer_or_admin)):
    text = await ResearchService.get_document_text(db_ro, document_id)
    snippet = text[:8000]

    prompt = (
        f"Analyze the following legal document (FIR, Charge sheet, or Judgment) and extract all chronological events.\n"
        f"Format the output strictly as a JSON list of objects. Each object must have fields 'date' (ISO-ish or natural format), "
        f"'description' (brief summary of event), and 'involved_parties' (key people involved).\n\n"
        f"Document Snippet:\n{snippet}\n\nJSON Output:"
    )

    system_prompt = "You are a legal document analyst. Output only valid JSON lists. Do not include chat explanations or markdown blocks."

    timeline = await OllamaService.generate_structured(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {
        "timeline": timeline,
        "disclaimer": "AI-generated content is for informational purposes only. It is not professional legal advice and must be independently verified by an advocate."
    }

@router.post("/analyze/facts")
async def extract_case_facts(document_id: int, model_name: str = "mistral:latest", db_ro: AsyncSession = Depends(get_db_ro), current_user: User = Depends(verify_lawyer_or_admin)):
    text = await ResearchService.get_document_text(db_ro, document_id)
    snippet = text[:8000]

    prompt = (
        f"Summarize the legal facts from the following text.\n"
        f"Identify the offense description, the sections invoked (IPC, BNS, CrPC, etc.), "
        f"the accused individuals, and the complaining/victim parties. "
        f"Format the output strictly as a JSON object with fields: 'offence', 'sections_invoked', 'accused', 'victims', 'summary'.\n\n"
        f"Document Snippet:\n{snippet}\n\nJSON Output:"
    )

    system_prompt = "You are an Indian criminal defense analyst. Output only valid JSON. Do not write text outside the JSON."

    facts = await OllamaService.generate_structured(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {
        "facts": facts,
        "disclaimer": "AI-generated content is for informational purposes only. It is not professional legal advice and must be independently verified by an advocate."
    }

@router.post("/audit/risk-scan")
async def scan_contract_risks(document_id: int, model_name: str = "mistral:latest", db_ro: AsyncSession = Depends(get_db_ro), current_user: User = Depends(verify_lawyer_or_admin)):
    text = await ResearchService.get_document_text(db_ro, document_id)
    snippet = text[:10000]

    prompt = (
        f"Perform an audit on this contract. Extract all clauses representing potential liability, termination terms, indemnity issues, "
        f"or high financial risks. For each risk found, rate it as 'High', 'Medium', or 'Low' risk.\n"
        f"Format response strictly as a JSON list of objects with fields: 'clause_title', 'risk_rating', 'summary', 'remediation_advice'.\n\n"
        f"Contract Snippet:\n{snippet}\n\nJSON Output:"
    )

    system_prompt = "You are an expert corporate contracts auditor. Output only valid JSON."

    risks = await OllamaService.generate_structured(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {
        "risks": risks,
        "disclaimer": "AI-generated content is for informational purposes only. It is not professional legal advice and must be independently verified by an advocate."
    }

@router.post("/audit/compare")
async def compare_clauses(doc_id_a: int, doc_id_b: int, model_name: str = "mistral:latest", db_ro: AsyncSession = Depends(get_db_ro), current_user: User = Depends(verify_lawyer_or_admin)):
    text_a = await ResearchService.get_document_text(db_ro, doc_id_a)
    text_b = await ResearchService.get_document_text(db_ro, doc_id_b)

    prompt = (
        f"Compare Document A with Document B. Identify the primary structural changes, discrepancies, or clause variations "
        f"between both legal texts (e.g. indemnity, liability ceilings, termination notice periods).\n"
        f"Format response strictly as a JSON list of objects with fields: 'clause_title', 'doc_a_provision', 'doc_b_provision', 'variance_type' (Addition/Deletion/Modification), 'risk_assessment'.\n\n"
        f"Document A:\n{text_a[:6000]}\n\nDocument B:\n{text_b[:6000]}\n\nJSON Output:"
    )

    system_prompt = "You are a contract negotiation expert. Output only valid JSON."

    comparison = await OllamaService.generate_structured(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {
        "comparison": comparison,
        "disclaimer": "AI-generated content is for informational purposes only. It is not professional legal advice and must be independently verified by an advocate."
    }

@router.post("/audit/simplify")
async def simplify_clause_endpoint(req: SimplifyClauseRequest, current_user: User = Depends(verify_lawyer_or_admin)):
    if check_prompt_injection(req.clause_text):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Potential prompt injection or instruction override attempt detected. Request blocked."
        )

    prompt = (
        "Translate the following complex legal clause into clear, plain English. "
        "Also extract the key rights it grants, and the critical liabilities or risks it imposes.\n\n"
        f"Clause text:\n{req.clause_text}\n\n"
        "Return the response strictly as a JSON object with these fields:\n"
        "{\n"
        "  \"plain_english\": \"plain English translation of the clause\",\n"
        "  \"key_rights\": \"bullet list or paragraph of key rights granted\",\n"
        "  \"critical_risks\": \"bullet list or paragraph of liabilities or risks imposed\"\n"
        "}"
    )
    
    system_prompt = "You are a professional legal auditor. Output only valid JSON."
    
    response_json = await OllamaService.generate_structured(
        model=req.model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )
    
    return {
        **response_json,
        "disclaimer": "AI-generated content is for informational purposes only. It is not professional legal advice and must be independently verified by an advocate."
    }

@router.get("/draft/templates")
def list_draft_templates(current_user: User = Depends(get_current_user)):
    return [
        {
            "id": "legal_notice",
            "name": "Legal Notice for Recovery of Dues",
            "fields": ["client_name", "debtor_name", "amount_due", "due_date", "notice_period_days"]
        },
        {
            "id": "bail_application",
            "name": "Bail Application under Section 439 CrPC (483 BNSS)",
            "fields": ["accused_name", "fir_number", "police_station", "offences_charged", "grounds_for_bail"]
        },
        {
            "id": "tenancy_agreement",
            "name": "Residential Tenancy Agreement",
            "fields": ["landlord_name", "tenant_name", "property_address", "monthly_rent", "security_deposit", "lease_term_months"]
        }
    ]

@router.post("/draft/generate")
async def generate_draft(template_id: str, fields: Dict[str, str], model_name: str = "mistral:latest", current_user: User = Depends(verify_lawyer_or_admin)):
    for k, v in fields.items():
        if check_prompt_injection(v):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Potential prompt injection or instruction override attempt detected in field '{k}'. Request blocked."
            )

    lang_instruction = ""
    if fields.get("language", "").lower() == "hindi":
        lang_instruction = "\nCRITICAL REQUIREMENT: The entire draft MUST be written in the HINDI language, using appropriate formal Indian legal terminology (e.g. Nyayalaya, Adhivakta). Do not output English except for case citations or specific statutory abbreviations if absolutely necessary.\n"
        
    prompt = (
        f"Draft a formal, legally enforceable Indian document of type: '{template_id}'.\n"
        f"Use the following custom details in the draft:\n{json.dumps(fields, indent=2)}\n\n"
        f"Ensure it strictly follows standard formatting in Indian courts, incorporates BNS/BNSS statutory terms where appropriate, "
        f"and leaves placeholders for signatures.{lang_instruction} Write the complete document draft text:"
    )

    system_prompt = "You are an experienced advocate in the Supreme Court of India. Write professional legal drafts."

    draft_text = await OllamaService.generate_completion(
        model=model_name,
        prompt=prompt,
        system_prompt=system_prompt
    )

    return {
        "draft": draft_text,
        "disclaimer": "AI-generated content is for informational purposes only. It is not professional legal advice and must be independently verified by an advocate."
    }

@router.post("/draft/format")
def format_legal_draft(req: FormatDraftRequest, current_user: User = Depends(verify_lawyer_or_admin)):
    formatted_lines = []
    
    if req.court_header == "supreme_court":
        header = (
            "IN THE SUPREME COURT OF INDIA\n"
            "(ORIGINAL JURISDICTION / CIVIL APPELLATE JURISDICTION)\n"
            "WRIT PETITION / APPEAL NO. ______ OF 2026\n\n"
            "IN THE MATTER OF:\n"
            "_________________________                     ... PETITIONER(S)\n"
            "      VERSUS\n"
            "_________________________                     ... RESPONDENT(S)\n\n"
            "================================================================================\n"
        )
        formatted_lines.append(header)
    elif req.court_header == "high_court":
        header = (
            "IN THE HIGH COURT OF DELHI AT NEW DELHI\n"
            "(ORDINARY ORIGINAL CIVIL JURISDICTION)\n"
            "O.S. NO. ______ OF 2026\n\n"
            "IN THE MATTER OF:\n"
            "_________________________                     ... PLAINTIFF\n"
            "      VERSUS\n"
            "_________________________                     ... DEFENDANT\n\n"
            "================================================================================\n"
        )
        formatted_lines.append(header)
    elif req.court_header == "district_court":
        header = (
            "IN THE COURT OF THE DISTRICT & SESSIONS JUDGE, SAKET COURTS, NEW DELHI\n"
            "CIVIL / CRIMINAL SUIT NO. ______ OF 2026\n\n"
            "IN THE MATTER OF:\n"
            "_________________________                     ... COMPLAINANT/PLAINTIFF\n"
            "      VERSUS\n"
            "_________________________                     ... ACCUSED/DEFENDANT\n\n"
            "================================================================================\n"
        )
        formatted_lines.append(header)
        
    raw_lines = req.draft_text.split("\n")
    margin_prefix = " " * req.margin_spaces
    for line in raw_lines:
        formatted_line = f"{margin_prefix}{line}"
        formatted_lines.append(formatted_line)
        
    separator = "\n\n" if req.line_spacing > 1.2 else "\n"
    final_text = separator.join(formatted_lines)
    
    return {"formatted_draft": final_text}

@router.post("/analyze/fir")
async def analyze_fir_documents(req: FIRAnalysisRequest, db: AsyncSession = Depends(get_db), db_ro: AsyncSession = Depends(get_db_ro), current_user: User = Depends(get_current_user)):
    try:
        result = await ResearchService.analyze_fir_documents(db_ro, req)
        await log_audit_trail(db, current_user.email, "FIR_ANALYZE", "documents", str(req.document_ids))
        return result
    except Exception as e:
        await safe_db_rollback(db)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/predict-outcome")
async def predict_case_outcome(req: PredictOutcomeRequest, current_user: User = Depends(get_current_user)):
    if check_prompt_injection(req.facts) or check_prompt_injection(req.sections) or check_prompt_injection(req.court):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Potential prompt injection or instruction override attempt detected in inputs. Request blocked."
        )

    system_prompt = """You are an expert Indian judicial analyst with 30+ years of Supreme Court and High Court experience. Based on the case facts, court type, and applicable legal sections provided, return a JSON object with:
- 'predicted_outcome': one of Likely to Succeed / Uncertain / Likely to Fail
- 'confidence_percentage': integer 0-100
- 'reasoning': list of 3-5 key reasoning points as strings
- 'similar_precedents': list of {case_name, citation, relevance} (well-known Indian cases)
- 'risk_factors': list of strings describing weaknesses in the case
- 'strengthening_suggestions': list of action items to improve case outcome
- 'estimated_timeline_months': integer estimate
Return ONLY valid JSON."""

    user_prompt = f"""Court: {req.court}\nApplicable Sections: {req.sections or 'Not specified'}\nCase Facts: {req.facts[:4000]}"""

    try:
        result = await OllamaService.generate_structured(
            model_name=req.model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_hint="{\"predicted_outcome\":\"\", \"confidence_percentage\":50, \"reasoning\":[], \"similar_precedents\":[], \"risk_factors\":[], \"strengthening_suggestions\":[], \"estimated_timeline_months\":12}"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/transcribe")
async def transcribe_audio(req: VoiceTranscribeRequest, current_user: User = Depends(get_current_user)):
    import base64, tempfile, subprocess, re
    try:
        if not re.match(r"^[a-zA-Z-]{2,10}$", req.language):
            raise HTTPException(status_code=400, detail="Invalid language identifier format.")

        audio_bytes = base64.b64decode(req.audio_base64)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        models = await OllamaService.get_available_models()
        whisper_available = any("whisper" in m.lower() for m in models)
        if whisper_available:
            model_name = next(m for m in models if "whisper" in m.lower())
            result = await OllamaService.generate_structured(
                model_name=model_name,
                system_prompt="Transcribe the audio content accurately. Return JSON: {\"transcript\": \"...\"}",
                user_prompt="Please transcribe the provided audio.",
                schema_hint="{\"transcript\": \"\"}"
            )
            return result
        else:
            proc = subprocess.run(["whisper", tmp_path, "--output_format", "txt", "--language", req.language],
                                  capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                transcript = proc.stdout.strip()
                return {"transcript": transcript}
            else:
                return {"transcript": "", "warning": "Whisper not available. Install 'openai-whisper' or pull whisper model in Ollama."}
    except Exception as e:
        return {"transcript": "", "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass

@router.get("/whatsapp/reminder/{schedule_id}")
async def generate_whatsapp_reminder(schedule_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await ResearchService.generate_whatsapp_reminder(db, schedule_id)
