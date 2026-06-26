import random
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_backend.database import Matter, Schedule
from aegis_backend.core.security import SECRET_KEY

class MatterService:
    @staticmethod
    async def sync_ecourts_cnr(db: AsyncSession, matter: Matter) -> Dict[str, Any]:
        """Simulates eCourts data synchronization for a given matter."""
        judges = ["Hon'ble Mr. Justice D. Y. Chandrachud", "Hon'ble Mrs. Justice Hima Kohli", "Hon'ble Mr. Justice Sanjiv Khanna"]
        status_choices = ["open", "pending_hearing", "closed"]
        courts = ["Supreme Court of India", "High Court of Delhi", "District Court of Saket"]
        
        cnr_seed = sum(ord(c) for c in matter.cnr_number)
        rng = random.Random(cnr_seed)
        
        fetched_court = rng.choice(courts)
        fetched_judge = rng.choice(judges)
        fetched_status = rng.choice(status_choices)
        
        hearing_date = datetime.now() + timedelta(days=10)
        
        matter.court = fetched_court
        matter.judge = fetched_judge
        matter.status = fetched_status
        
        stmt_schedule = select(Schedule).filter(
            Schedule.matter_id == matter.id, 
            Schedule.schedule_type == "hearing"
        )
        res_schedule = await db.execute(stmt_schedule)
        existing_schedule = res_schedule.scalars().first()
        
        if not existing_schedule:
            new_s = Schedule(
                matter_id=matter.id,
                title="eCourts Synced Hearing Date",
                schedule_type="hearing",
                target_date=hearing_date,
                notes=f"Automatically synchronized and locked via eCourts CNR {matter.cnr_number}"
            )
            db.add(new_s)
        else:
            existing_schedule.target_date = hearing_date
            existing_schedule.notes = f"Updated via eCourts CNR sync on {datetime.now().strftime('%Y-%m-%d')}"
            
        matter.is_locked = True
        
        payload = f"{matter.id}:{matter.case_number}:{matter.court}:{matter.judge}:{matter.status}"
        matter.hmac_signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        
        await db.commit()
        await db.refresh(matter)
        
        return {
            "status": "success", 
            "message": "Data synchronized successfully and immediately locked locally. Connection disconnected. (eCourts Sync Simulation Mode)",
            "is_simulation": True,
            "court": fetched_court,
            "judge": fetched_judge,
            "hearing_date": hearing_date.isoformat()
        }
