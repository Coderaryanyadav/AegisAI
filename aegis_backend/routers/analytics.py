from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from aegis_backend.database import get_db, User, Client, Matter, Document, Invoice, Schedule
from aegis_backend.core.security import get_current_user

router = APIRouter(tags=["analytics"])

@router.get("/analytics/summary")
async def analytics_summary(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_clients = (await db.execute(select(func.count(Client.id)))).scalar()
    total_matters = (await db.execute(select(func.count(Matter.id)))).scalar()
    open_matters = (await db.execute(select(func.count(Matter.id)).filter(Matter.status == "open"))).scalar()
    closed_matters = (await db.execute(select(func.count(Matter.id)).filter(Matter.status == "closed"))).scalar()
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar()
    total_invoices = (await db.execute(select(func.count(Invoice.id)))).scalar()
    paid_invoices = (await db.execute(select(func.count(Invoice.id)).filter(Invoice.status == "paid"))).scalar()
    unpaid_invoices = (await db.execute(select(func.count(Invoice.id)).filter(Invoice.status == "unpaid"))).scalar()
    
    # Revenue totals
    res_paid = await db.execute(select(func.sum(Invoice.grand_total)).filter(Invoice.status == "paid"))
    total_revenue = res_paid.scalar() or 0.0
    
    res_pending = await db.execute(select(func.sum(Invoice.grand_total)).filter(Invoice.status == "unpaid"))
    pending_revenue = res_pending.scalar() or 0.0

    # Upcoming hearings in next 7 days
    now = datetime.now(timezone.utc).isoformat()
    week_later = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    
    stmt_upcoming = select(Schedule).filter(
        Schedule.is_completed == False,
        Schedule.target_date >= now,
        Schedule.target_date <= week_later
    ).order_by(Schedule.target_date).limit(10)
    
    res_upcoming = await db.execute(stmt_upcoming)
    upcoming = res_upcoming.scalars().all()

    # Recent invoices
    stmt_recent = select(Invoice).order_by(Invoice.created_at.desc()).limit(5)
    res_recent = await db.execute(stmt_recent)
    recent_invoices = res_recent.scalars().all()

    return {
        "total_clients": total_clients,
        "total_matters": total_matters,
        "open_matters": open_matters,
        "closed_matters": closed_matters,
        "total_documents": total_docs,
        "total_invoices": total_invoices,
        "paid_invoices": paid_invoices,
        "unpaid_invoices": unpaid_invoices,
        "total_revenue_inr": round(total_revenue, 2),
        "pending_revenue_inr": round(pending_revenue, 2),
        "upcoming_hearings": [
            {"id": s.id, "title": s.title, "schedule_type": s.schedule_type,
             "target_date": s.target_date, "matter_id": s.matter_id}
            for s in upcoming
        ],
        "recent_invoices": [
            {"invoice_number": i.invoice_number, "grand_total": i.grand_total, "status": i.status}
            for i in recent_invoices
        ]
    }

