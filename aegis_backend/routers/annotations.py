from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from aegis_backend.database import get_db, User, Annotation
from aegis_backend.schemas.models import AnnotationCreate
from aegis_backend.core.security import get_current_user

router = APIRouter(tags=["annotations"])

@router.post("/annotations")
async def create_annotation(req: AnnotationCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from aegis_backend.core.security import check_document_access
    await check_document_access(db, current_user, req.document_id)
    
    ann = Annotation(
        document_id=req.document_id,
        user_email=current_user.email,
        selected_text=req.selected_text,
        note=req.note,
        color=req.color,
        page_hint=req.page_hint
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return {"id": ann.id, "message": "Annotation saved"}

@router.get("/annotations/{document_id}")
async def get_annotations(document_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from aegis_backend.core.security import check_document_access
    await check_document_access(db, current_user, document_id)
    
    stmt = select(Annotation).filter(
        Annotation.document_id == document_id,
        Annotation.user_email == current_user.email
    ).order_by(Annotation.created_at.desc())
    res = await db.execute(stmt)
    anns = res.scalars().all()
    return [
        {"id": a.id, "selected_text": a.selected_text, "note": a.note,
         "color": a.color, "page_hint": a.page_hint, "created_at": a.created_at.isoformat()}
        for a in anns
    ]

@router.delete("/annotations/{annotation_id}")
async def delete_annotation(annotation_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = select(Annotation).filter(
        Annotation.id == annotation_id,
        Annotation.user_email == current_user.email
    )
    res = await db.execute(stmt)
    ann = res.scalars().first()
    if not ann:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(ann)
    await db.commit()
    return {"message": "Deleted"}

