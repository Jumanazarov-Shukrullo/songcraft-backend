"""User feedback routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from ...db.database import get_db
from ...infrastructure.orm.user_model import UserModel
from ...infrastructure.orm.feedback_model import FeedbackModel
from ...api.dependencies import get_current_user

router = APIRouter()


class FeedbackCreate(BaseModel):
    subject: str
    message: str
    category: str = "general"  # general, bug, feature, improvement


class AnonymousFeedbackCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    subject: str
    message: str
    category: str = "general"  # general, bug, feature, improvement


class FeedbackResponse(BaseModel):
    id: int
    subject: str
    message: str
    category: str
    status: str
    admin_response: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit new feedback."""
    try:
        feedback = FeedbackModel(
            user_id=current_user.id,
            subject=feedback_data.subject,
            message=feedback_data.message,
            category=feedback_data.category,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        return feedback
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/", response_model=List[FeedbackResponse])
async def get_user_feedback(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's feedback."""
    try:
        feedback = db.query(FeedbackModel).filter(
            FeedbackModel.user_id == current_user.id
        ).order_by(FeedbackModel.created_at.desc()).all()
        
        return feedback
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load feedback: {str(e)}"
        )


@router.post("/anonymous", response_model=FeedbackResponse)
async def submit_anonymous_feedback(
    feedback_data: AnonymousFeedbackCreate,
    db: Session = Depends(get_db)
):
    """Submit anonymous feedback (no authentication required)."""
    try:
        feedback = FeedbackModel(
            user_id=None,  # Anonymous
            name=feedback_data.name,
            email=feedback_data.email,
            subject=feedback_data.subject,
            message=feedback_data.message,
            category=feedback_data.category,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        return feedback
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(
    feedback_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific feedback by ID."""
    feedback = db.query(FeedbackModel).filter(
        FeedbackModel.id == feedback_id,
        FeedbackModel.user_id == current_user.id
    ).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return feedback 