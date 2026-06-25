from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str = "lawyer"

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    firm_logo: Optional[str] = None
    firm_name: Optional[str] = None

    class Config:
        from_attributes = True

class FirmSettingsUpdate(BaseModel):
    firm_name: str
    firm_logo: Optional[str] = None

class ClientCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

class ClientResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MatterCreate(BaseModel):
    client_id: int
    case_number: Optional[str] = None
    title: str
    court: Optional[str] = None
    judge: Optional[str] = None
    opponent_name: Optional[str] = None
    opposing_advocate: Optional[str] = None
    status: str = "open"
    facts: Optional[str] = None
    cnr_number: Optional[str] = None

class MatterResponse(BaseModel):
    id: int
    client_id: int
    case_number: Optional[str] = None
    title: str
    court: Optional[str] = None
    judge: Optional[str] = None
    opponent_name: Optional[str] = None
    opposing_advocate: Optional[str] = None
    status: str
    facts: Optional[str] = None
    cnr_number: Optional[str] = None
    is_locked: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ScheduleCreate(BaseModel):
    matter_id: int
    title: str
    schedule_type: str  # hearing, deadline, meeting
    target_date: str
    notes: Optional[str] = None

class ScheduleResponse(BaseModel):
    id: int
    matter_id: int
    title: str
    schedule_type: str
    target_date: str
    notes: Optional[str] = None
    is_completed: bool

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: int
    matter_id: Optional[int] = None
    original_name: str
    stored_uuid: str
    file_path: str
    file_hash: str
    status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class ResearchQuery(BaseModel):
    query: str
    matter_ids: Optional[List[int]] = None
    model_name: str = "mistral:latest"

class ConflictCheckRequest(BaseModel):
    client_name: str
    opponent_name: str
    facts: Optional[str] = None

class FormatDraftRequest(BaseModel):
    draft_text: str
    court_header: str = "none" # none, supreme_court, high_court, district_court
    line_spacing: float = 1.5
    margin_spaces: int = 4

class SimplifyClauseRequest(BaseModel):
    clause_text: str
    model_name: str = "mistral:latest"

class TimeEntryCreate(BaseModel):
    matter_id: int
    description: str
    hours: str
    rate_per_hour: str = "5000"
    date: str

class InvoiceCreate(BaseModel):
    client_id: int
    matter_id: Optional[int] = None
    notes: Optional[str] = None

class InvoiceStatusUpdate(BaseModel):
    status: str  # unpaid, paid, overdue

class AnnotationCreate(BaseModel):
    document_id: int
    selected_text: str
    note: Optional[str] = None
    color: str = "yellow"
    page_hint: Optional[str] = None

class TwoFASetupVerify(BaseModel):
    totp_code: str

class FIRAnalysisRequest(BaseModel):
    document_ids: List[int]
    model_name: str = "mistral:latest"

class PredictOutcomeRequest(BaseModel):
    facts: str
    court: str = "District Court"
    sections: Optional[str] = None
    model_name: str = "mistral:latest"

class VoiceTranscribeRequest(BaseModel):
    audio_base64: str  # base64 encoded wav/mp3
    language: str = "en"
