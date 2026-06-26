import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func

from aegis_backend.database import get_db, User, Client, Matter, TimeEntry, Invoice
from aegis_backend.schemas.models import TimeEntryCreate, InvoiceCreate, InvoiceStatusUpdate
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin, log_audit_trail

router = APIRouter(tags=["billing"])

@router.post("/billing/time-entry")
async def create_time_entry(entry: TimeEntryCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    new_entry = TimeEntry(
        matter_id=entry.matter_id,
        user_email=current_user.email,
        description=entry.description,
        hours=entry.hours,
        rate_per_hour=entry.rate_per_hour,
        date=entry.date
    )
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)
    await log_audit_trail(db, current_user.email, "CREATE", "time_entry", str(new_entry.id))
    return {"id": new_entry.id, "message": "Time entry logged"}

@router.get("/billing/time-entries")
async def get_time_entries(response: Response, matter_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from aegis_backend.core.security import check_matter_access
    await check_matter_access(db, current_user, matter_id)
    
    stmt = select(TimeEntry).filter(TimeEntry.matter_id == matter_id)
    
    count_stmt = select(func.count(TimeEntry.id)).filter(TimeEntry.matter_id == matter_id)
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar()
    response.headers["X-Total-Count"] = str(total_count)
    
    res = await db.execute(stmt.order_by(TimeEntry.created_at.desc()).offset(skip).limit(limit))
    entries = res.scalars().all()
    return [
        {"id": e.id, "description": e.description, "hours": e.hours, "rate_per_hour": e.rate_per_hour,
         "date": e.date, "amount": str((Decimal(e.hours) * Decimal(e.rate_per_hour)).quantize(Decimal("0.01")))}
        for e in entries
    ]

@router.delete("/billing/time-entry/{entry_id}")
async def delete_time_entry(entry_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    stmt = select(TimeEntry).filter(TimeEntry.id == entry_id)
    res = await db.execute(stmt)
    entry = res.scalars().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)
    await db.commit()
    return {"message": "Deleted"}

@router.post("/billing/invoice")
async def create_invoice(req: InvoiceCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    from aegis_backend.services.billing_service import BillingService
    
    gst_rate_val = getattr(current_user, "gst_rate", Decimal("18.0"))
    if gst_rate_val is None:
        gst_rate = Decimal("18.0")
    else:
        gst_rate = Decimal(str(gst_rate_val))
        
    try:
        invoice = await BillingService.create_invoice(db, req.client_id, req.matter_id, req.notes, gst_rate)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
        
    await log_audit_trail(db, current_user.email, "CREATE", "invoice", invoice.invoice_number)
    return {
        "id": invoice.id, "invoice_number": invoice.invoice_number,
        "total_amount": invoice.total_amount, "gst_amount": invoice.gst_amount,
        "grand_total": invoice.grand_total, "status": invoice.status,
        "created_at": invoice.created_at.isoformat()
    }

@router.get("/billing/invoices")
async def list_invoices(response: Response, client_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Invoice)
    if current_user.role == "client":
        stmt_client = select(Client).filter(Client.email == current_user.email)
        res_client = await db.execute(stmt_client)
        client = res_client.scalars().first()
        if not client:
            response.headers["X-Total-Count"] = "0"
            return []
        stmt = stmt.filter(Invoice.client_id == client.id)
    elif client_id:
        stmt = stmt.filter(Invoice.client_id == client_id)
        
    count_stmt = select(func.count(Invoice.id)).select_from(stmt.subquery())
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar()
    response.headers["X-Total-Count"] = str(total_count)
    
    res = await db.execute(stmt.order_by(Invoice.created_at.desc()).offset(skip).limit(limit))
    invoices = res.scalars().all()
    return [
        {"id": i.id, "invoice_number": i.invoice_number, "client_id": i.client_id,
         "matter_id": i.matter_id, "total_amount": i.total_amount, "gst_amount": i.gst_amount,
         "grand_total": i.grand_total, "status": i.status, "notes": i.notes,
         "created_at": i.created_at.isoformat()}
        for i in invoices
    ]

@router.put("/billing/invoice/{invoice_id}/status")
async def update_invoice_status(invoice_id: int, req: InvoiceStatusUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin)):
    stmt = select(Invoice).filter(Invoice.id == invoice_id)
    res = await db.execute(stmt)
    inv = res.scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv.status = req.status
    await db.commit()
    return {"message": "Status updated", "status": req.status}

