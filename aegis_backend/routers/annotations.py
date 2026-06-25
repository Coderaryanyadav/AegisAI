from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from aegis_backend.database import get_db, User, Annotation
from aegis_backend.schemas.models import AnnotationCreate
from aegis_backend.core.security import get_current_user

router = APIRouter(prefix="/api", tags=["annotations"])

@router.post("/annotations")
def create_annotation(req: AnnotationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ann = Annotation(
        document_id=req.document_id,
        user_email=current_user.email,
        selected_text=req.selected_text,
        note=req.note,
        color=req.color,
        page_hint=req.page_hint
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return {"id": ann.id, "message": "Annotation saved"}

@router.get("/annotations/{document_id}")
def get_annotations(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    anns = db.query(Annotation).filter(
        Annotation.document_id == document_id,
        Annotation.user_email == current_user.email
    ).order_by(Annotation.created_at.desc()).all()
    return [
        {"id": a.id, "selected_text": a.selected_text, "note": a.note,
         "color": a.color, "page_hint": a.page_hint, "created_at": a.created_at.isoformat()}
        for a in anns
    ]

@router.delete("/annotations/{annotation_id}")
def delete_annotation(annotation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ann = db.query(Annotation).filter(Annotation.id == annotation_id, Annotation.user_email == current_user.email).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(ann)
    db.commit()
    return {"message": "Deleted"}
