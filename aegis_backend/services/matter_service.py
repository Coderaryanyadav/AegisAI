import hashlib
import hmac
from typing import List, Tuple, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from aegis_backend.database import Matter, User
from aegis_backend.repositories.matter_repository import MatterRepository
from aegis_backend.schemas.models import MatterCreate, MatterUpdate, ConflictCheckRequest
from aegis_backend.core.security import SECRET_KEY
from aegis_backend.services.client_service import ClientService

class MatterService:
    @staticmethod
    async def get_matters_list(
        db: AsyncSession,
        current_user: User,
        client_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Matter], int]:
        repo = MatterRepository(db)
        target_client_id = client_id

        if current_user.role == "client":
            client = await repo.get_client_by_email(current_user.email)
            if not client:
                return [], 0
            target_client_id = client.id

        matters, total_count = await repo.list_matters(client_id=target_client_id, skip=skip, limit=limit)

        for m in matters:
            if m.is_locked and m.hmac_signature:
                payload = f"{m.id}:{m.case_number}:{m.court}:{m.judge}:{m.status}"
                expected_hmac = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(m.hmac_signature, expected_hmac):
                    m.status = "TAMPERED_LOCK" # Warn user of DB tampering

        return matters, total_count

    @staticmethod
    async def create_matter(db: AsyncSession, matter_in: MatterCreate) -> Matter:
        repo = MatterRepository(db)
        matter = Matter(
            client_id=matter_in.client_id,
            case_number=matter_in.case_number,
            title=matter_in.title,
            court=matter_in.court,
            judge=matter_in.judge,
            opponent_name=matter_in.opponent_name,
            opposing_advocate=matter_in.opposing_advocate,
            status=matter_in.status,
            facts=matter_in.facts,
            cnr_number=matter_in.cnr_number
        )
        return await repo.create(matter)

    @staticmethod
    async def delete_matter(db: AsyncSession, matter_id: int):
        repo = MatterRepository(db)
        matter = await repo.get_by_id(matter_id)
        if not matter:
            raise HTTPException(status_code=404, detail="Matter not found")
        
        # Cascade clean documents, files, and vectors belonging to this matter
        await ClientService.cleanup_matter_documents(db, matter.id)
        
        await repo.delete(matter)

    @staticmethod
    async def update_matter(db: AsyncSession, matter_id: int, matter_in: MatterUpdate) -> Matter:
        repo = MatterRepository(db)
        matter = await repo.get_by_id(matter_id)
        if not matter:
            raise HTTPException(status_code=404, detail="Matter not found")
            
        update_data = matter_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(matter, field, value)
            
        return await repo.update(matter)

    @staticmethod
    async def check_legal_conflict(db: AsyncSession, req: ConflictCheckRequest) -> Dict:
        repo = MatterRepository(db)
        conflict_detected = False
        severity = "low"
        reasons = []

        clean_client = req.client_name.strip().upper()
        clean_opponent = req.opponent_name.strip().upper()

        if not clean_client or not clean_opponent:
            raise HTTPException(status_code=400, detail="Client name and Opponent name are required.")

        # 1. Check direct conflicts
        clients = await repo.check_direct_conflict(clean_opponent)
        for c in clients:
            conflict_detected = True
            severity = "high"
            reasons.append(f"DIRECT CONFLICT: Opponent '{req.opponent_name}' matches active client folder '{c.name}' (Client ID: {c.id}).")

        # 2. Check indirect conflicts (matters)
        matters = await repo.check_indirect_conflict(clean_client, clean_opponent)
        
        for m in matters:
            if m.opponent_name:
                clean_matter_opp = m.opponent_name.strip().upper()
                if clean_client in clean_matter_opp or clean_matter_opp in clean_client:
                    conflict_detected = True
                    severity = "high"
                    reasons.append(f"INDIRECT CONFLICT: Prospective client '{req.client_name}' is listed as Opponent in active matter file '{m.title}' (Matter ID: {m.id}, Client: {m.client.name if m.client else 'Unknown'}).")
            
            if m.client:
                clean_matter_client = m.client.name.strip().upper()
                if clean_opponent in clean_matter_client or clean_matter_client in clean_opponent:
                    conflict_detected = True
                    if severity != "high":
                        severity = "medium"
                    reasons.append(f"ASSOCIATED RISK: Prospective opponent '{req.opponent_name}' matches client '{m.client.name}' in matter file '{m.title}'.")

        return {
            "client_name": req.client_name,
            "opponent_name": req.opponent_name,
            "conflict_detected": conflict_detected,
            "severity": severity,
            "reasons": reasons
        }
