from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aegis_backend.database import get_db, User, Client, Matter, Document, Invoice, Schedule
from aegis_backend.core.security import get_current_user

router = APIRouter(prefix="/api", tags=["analytics"])

@router.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_clients = db.query(Client).count()
    total_matters = db.query(Matter).count()
    open_matters = db.query(Matter).filter(Matter.status == "open").count()
    closed_matters = db.query(Matter).filter(Matter.status == "closed").count()
    total_docs = db.query(Document).count()
    total_invoices = db.query(Invoice).count()
    paid_invoices = db.query(Invoice).filter(Invoice.status == "paid").count()
    unpaid_invoices = db.query(Invoice).filter(Invoice.status == "unpaid").count()
    
    # Revenue totals
    all_paid = db.query(Invoice).filter(Invoice.status == "paid").all()
    total_revenue = sum(float(i.grand_total) for i in all_paid)
    pending_revenue_invs = db.query(Invoice).filter(Invoice.status == "unpaid").all()
    pending_revenue = sum(float(i.grand_total) for i in pending_revenue_invs)

    # Upcoming hearings in next 7 days
    now = datetime.now(timezone.utc).isoformat()
    week_later = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    upcoming = db.query(Schedule).filter(
        Schedule.is_completed == False,
        Schedule.target_date >= now,
        Schedule.target_date <= week_later
    ).order_by(Schedule.target_date).limit(10).all()

    # Recent invoices
    recent_invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(5).all()

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
