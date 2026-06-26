import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from aegis_backend.database import Client, Matter, TimeEntry, Invoice

class BillingService:
    @staticmethod
    async def create_invoice(db: AsyncSession, client_id: int, matter_id: int | None, notes: str | None, gst_rate: Decimal) -> Invoice:
        # Verify client exists
        client_res = await db.execute(select(Client).filter(Client.id == client_id))
        if not client_res.scalars().first():
            raise ValueError("Invalid client_id: client does not exist")
        
        if matter_id:
            matter_res = await db.execute(select(Matter).filter(Matter.id == matter_id))
            if not matter_res.scalars().first():
                raise ValueError("Invalid matter_id: matter does not exist")
            stmt = select(TimeEntry).filter(TimeEntry.matter_id == matter_id)
            res = await db.execute(stmt)
            entries = res.scalars().all()
        else:
            entries = []
            
        total = Decimal("0.00")
        for e in entries:
            total += Decimal(e.hours) * Decimal(e.rate_per_hour)
            
        gst = (total * (gst_rate / Decimal("100.0"))).quantize(Decimal("0.01"))
        grand = (total + gst).quantize(Decimal("0.01"))
        
        success = False
        invoice = None
        for attempt in range(3):
            inv_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            invoice = Invoice(
                client_id=client_id,
                matter_id=matter_id,
                invoice_number=inv_number,
                total_amount=str(total.quantize(Decimal("0.01"))),
                gst_amount=str(gst),
                grand_total=str(grand),
                notes=notes
            )
            db.add(invoice)
            try:
                await db.commit()
                await db.refresh(invoice)
                success = True
                break
            except IntegrityError:
                await db.rollback()
                
        if not success:
            raise RuntimeError("Could not generate unique invoice number after retries")
            
        return invoice
