import re
from typing import List, Optional, Dict, Literal
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, field_validator, Field

class UserRegister(BaseModel):
    email: EmailStr
    password: str


    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character.")
        return v

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    firm_logo: Optional[str] = None
    firm_name: Optional[str] = None
    gst_rate: Optional[float] = 18.0
    is_disabled: bool = False

    class Config:
        from_attributes = True

class FirmSettingsUpdate(BaseModel):
    firm_name: str
    firm_logo: Optional[str] = None
    gst_rate: Optional[float] = 18.0

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
    status: Literal["open", "pending_hearing", "closed", "archived"] = "open"
    facts: Optional[str] = None
    cnr_number: Optional[str] = None

class MatterUpdate(BaseModel):
    title: Optional[str] = None
    case_number: Optional[str] = None
    court: Optional[str] = None
    judge: Optional[str] = None
    opponent_name: Optional[str] = None
    opposing_advocate: Optional[str] = None
    status: Optional[Literal["open", "pending_hearing", "closed", "archived"]] = None
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
    schedule_type: Literal["hearing", "deadline", "meeting"]  # hearing, deadline, meeting
    target_date: datetime
    notes: Optional[str] = None

class ScheduleResponse(BaseModel):
    id: int
    matter_id: int
    title: str
    schedule_type: str
    target_date: datetime
    notes: Optional[str] = None
    is_completed: bool

    class Config:
        from_attributes = True

class DocumentResponse(BaseModel):
    id: int
    matter_id: Optional[int] = None
    original_name: str
    stored_uuid: str
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
    line_spacing: float = Field(default=1.5, ge=1.0, le=5.0)
    margin_spaces: int = Field(default=4, ge=0, le=20)

class SimplifyClauseRequest(BaseModel):
    clause_text: str
    model_name: str = "mistral:latest"

class TimeEntryCreate(BaseModel):
    matter_id: int
    description: str
    hours: float = Field(..., ge=0)
    rate_per_hour: float = Field(default=5000.0, ge=0)
    date: date

class InvoiceCreate(BaseModel):
    client_id: int
    matter_id: Optional[int] = None
    notes: Optional[str] = None

class InvoiceStatusUpdate(BaseModel):
    status: Literal["unpaid", "paid", "overdue"]  # unpaid, paid, overdue

class AnnotationCreate(BaseModel):
    document_id: int
    selected_text: str
    note: Optional[str] = None
    color: Literal["yellow", "red", "green", "blue", "purple"] = "yellow"
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
