import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from aegis_backend.database import get_db, User, Client, Matter, TimeEntry, Invoice
from aegis_backend.schemas.models import TimeEntryCreate, InvoiceCreate, InvoiceStatusUpdate
from aegis_backend.core.security import get_current_user, log_audit_trail

router = APIRouter(prefix="/api", tags=["billing"])

@router.post("/billing/time-entry")
def create_time_entry(entry: TimeEntryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_entry = TimeEntry(
        matter_id=entry.matter_id,
        user_email=current_user.email,
        description=entry.description,
        hours=entry.hours,
        rate_per_hour=entry.rate_per_hour,
        date=entry.date
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    log_audit_trail(db, current_user.email, "CREATE", "time_entry", str(new_entry.id))
    return {"id": new_entry.id, "message": "Time entry logged"}

@router.get("/billing/time-entries")
def get_time_entries(matter_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entries = db.query(TimeEntry).filter(TimeEntry.matter_id == matter_id).order_by(TimeEntry.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {"id": e.id, "description": e.description, "hours": e.hours, "rate_per_hour": e.rate_per_hour,
         "date": e.date, "amount": str((Decimal(e.hours) * Decimal(e.rate_per_hour)).quantize(Decimal("0.01")))}
        for e in entries
    ]

@router.delete("/billing/time-entry/{entry_id}")
def delete_time_entry(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Deleted"}

@router.post("/billing/invoice")
def create_invoice(req: InvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entries = db.query(TimeEntry).filter(TimeEntry.matter_id == req.matter_id).all() if req.matter_id else []
    total = Decimal("0.00")
    for e in entries:
        total += Decimal(e.hours) * Decimal(e.rate_per_hour)
    gst = (total * Decimal("0.18")).quantize(Decimal("0.01"))
    grand = (total + gst).quantize(Decimal("0.01"))
    inv_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    invoice = Invoice(
        client_id=req.client_id,
        matter_id=req.matter_id,
        invoice_number=inv_number,
        total_amount=str(total.quantize(Decimal("0.01"))),
        gst_amount=str(gst),
        grand_total=str(grand),
        notes=req.notes
    )
    db.add(invoice)
    for attempt in range(3):
        try:
            db.commit()
            db.refresh(invoice)
            break
        except IntegrityError:
            db.rollback()
            invoice.invoice_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            attempt += 1
            if attempt >= 3:
                raise HTTPException(status_code=500, detail="Could not generate unique invoice number after retries")
    log_audit_trail(db, current_user.email, "CREATE", "invoice", invoice.invoice_number)
    return {
        "id": invoice.id, "invoice_number": invoice.invoice_number,
        "total_amount": invoice.total_amount, "gst_amount": invoice.gst_amount,
        "grand_total": invoice.grand_total, "status": invoice.status,
        "created_at": invoice.created_at.isoformat()
    }

@router.get("/billing/invoices")
def list_invoices(client_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Invoice)
    if current_user.role == "client":
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if not client:
            return []
        query = query.filter(Invoice.client_id == client.id)
    elif client_id:
        query = query.filter(Invoice.client_id == client_id)
    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {"id": i.id, "invoice_number": i.invoice_number, "client_id": i.client_id,
         "matter_id": i.matter_id, "total_amount": i.total_amount, "gst_amount": i.gst_amount,
         "grand_total": i.grand_total, "status": i.status, "notes": i.notes,
         "created_at": i.created_at.isoformat()}
        for i in invoices
    ]

@router.put("/billing/invoice/{invoice_id}/status")
def update_invoice_status(invoice_id: int, req: InvoiceStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv.status = req.status
    db.commit()
    return {"message": "Status updated", "status": req.status}
