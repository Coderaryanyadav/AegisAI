import os
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

logger = logging.getLogger("aegis_ai.backend")

from aegis_backend.database import get_db, User, Client, Matter, Document
from aegis_backend.schemas.models import ClientCreate, ClientResponse
from aegis_backend.core.security import get_current_user, verify_lawyer_or_admin, verify_offline_mode, log_audit_trail
from aegis_backend.core.cache import rag_cache
from aegis_backend.vector_store import vector_store

from aegis_backend.services.client_service import ClientService

router = APIRouter(tags=["clients"])

@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(response: Response, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    clients, total_count = await ClientService.get_clients_list(db, current_user, skip, limit)
    response.headers["X-Total-Count"] = str(total_count)
    return clients

@router.post("/clients", response_model=ClientResponse)
async def create_client(client_in: ClientCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    client = await ClientService.create_client(db, client_in)
    await log_audit_trail(db, current_user.email, "CREATE", "clients", str(client.id))
    return client

@router.delete("/clients/{id}")
async def delete_client(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(verify_lawyer_or_admin), _ = Depends(verify_offline_mode)):
    await ClientService.delete_client(db, id)
    
    # Invalidate RAG Cache
    rag_cache.clear()

    await log_audit_trail(db, current_user.email, "DELETE", "clients", str(id))
    return {"status": "success"}

@router.get("/crm/entity-graph")
async def get_crm_entity_graph(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generates an interconnected legal entity and conflict network graph."""
    stmt_clients = select(Client)
    res_clients = await db.execute(stmt_clients)
    clients = res_clients.scalars().all()

    stmt_matters = select(Matter)
    res_matters = await db.execute(stmt_matters)
    matters = res_matters.scalars().all()

    nodes = []
    edges = []
    seen_nodes = set()
    client_names = {c.name.strip().lower(): c for c in clients}
    conflicts = []

    for c in clients:
        c_id = f"client_{c.id}"
        if c_id not in seen_nodes:
            seen_nodes.add(c_id)
            nodes.append({
                "id": c_id,
                "label": c.name,
                "type": "client",
                "sublabel": c.email or c.phone or "Client",
                "color": "#10b981"  # Emerald
            })

    for m in matters:
        m_id = f"matter_{m.id}"
        if m_id not in seen_nodes:
            seen_nodes.add(m_id)
            nodes.append({
                "id": m_id,
                "label": m.title,
                "type": "matter",
                "sublabel": m.court or m.status,
                "color": "#3b82f6"  # Blue
            })

        # Edge from client to matter
        c_node = f"client_{m.client_id}"
        if c_node in seen_nodes:
            edges.append({
                "id": f"e_{c_node}_{m_id}",
                "source": c_node,
                "target": m_id,
                "label": "Retains"
            })

        if m.opponent_name:
            opp_name = m.opponent_name.strip()
            opp_id = f"opp_{abs(hash(opp_name.lower()))}"
            if opp_id not in seen_nodes:
                seen_nodes.add(opp_id)
                # Check for direct conflict
                is_conflicted = opp_name.lower() in client_names
                if is_conflicted:
                    conflicts.append({
                        "type": "Direct Opponent is Client",
                        "entity": opp_name,
                        "matter_id": m.id,
                        "matter_title": m.title,
                        "severity": "CRITICAL"
                    })

                nodes.append({
                    "id": opp_id,
                    "label": opp_name,
                    "type": "opponent",
                    "sublabel": "Direct Conflict!" if is_conflicted else "Opposing Party",
                    "color": "#ef4444" if is_conflicted else "#f59e0b"  # Red if conflict, Amber if standard
                })

            edges.append({
                "id": f"e_{m_id}_{opp_id}",
                "source": m_id,
                "target": opp_id,
                "label": "Adverse To"
            })

            if m.opposing_advocate:
                adv_name = m.opposing_advocate.strip()
                adv_id = f"adv_{abs(hash(adv_name.lower()))}"
                if adv_id not in seen_nodes:
                    seen_nodes.add(adv_id)
                    nodes.append({
                        "id": adv_id,
                        "label": adv_name,
                        "type": "advocate",
                        "sublabel": "Opposing Counsel",
                        "color": "#8b5cf6"  # Violet
                    })

                edges.append({
                    "id": f"e_{opp_id}_{adv_id}",
                    "source": opp_id,
                    "target": adv_id,
                    "label": "Represented By"
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "conflicts": conflicts
    }

