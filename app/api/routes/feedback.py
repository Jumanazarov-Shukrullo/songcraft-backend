"""User feedback routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from ...db.database import get_db
from ...infrastructure.orm.user_model import UserModel
from ...infrastructure.orm.feedback_model import FeedbackModel
from ...api.dependencies import get_current_user_model, get_current_admin_user_model

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


class AdminResponseCreate(BaseModel):
    """DTO for admin responding to feedback"""
    admin_response: str
    status: str = "resolved"  # pending, in_progress, resolved, dismissed


class FeedbackResponse(BaseModel):
    id: UUID
    subject: str
    message: str
    category: str
    status: str
    admin_response: Optional[str]
    created_at: datetime
    updated_at: datetime
    # Additional fields for user experience
    user_id: Optional[UUID] = None  # For admin view
    user_email: Optional[str] = None  # For anonymous feedback
    user_name: Optional[str] = None  # For anonymous feedback
    has_admin_response: bool = False  # Quick check for frontend

    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm_with_extras(cls, feedback: FeedbackModel):
        """Create response with computed fields"""
        return cls(
            id=feedback.id,
            subject=feedback.subject,
            message=feedback.message,
            category=feedback.category,
            status=feedback.status,
            admin_response=feedback.admin_response,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
            user_id=feedback.user_id,
            user_email=feedback.email,
            user_name=feedback.name,
            has_admin_response=bool(feedback.admin_response)
        )


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    current_user: UserModel = Depends(get_current_user_model),
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
        
        return FeedbackResponse.from_orm_with_extras(feedback)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/", response_model=List[FeedbackResponse])
async def get_user_feedback(
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get current user's feedback."""
    try:
        feedback = db.query(FeedbackModel).filter(
            FeedbackModel.user_id == current_user.id
        ).order_by(FeedbackModel.created_at.desc()).all()
        
        return [FeedbackResponse.from_orm_with_extras(f) for f in feedback]
        
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
        
        return FeedbackResponse.from_orm_with_extras(feedback)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(
    feedback_id: UUID,
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get specific feedback by ID."""
    feedback = db.query(FeedbackModel).filter(
        FeedbackModel.id == feedback_id,
        FeedbackModel.user_id == current_user.id
    ).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return FeedbackResponse.from_orm_with_extras(feedback)


# Admin endpoints for managing feedback
@router.put("/{feedback_id}/respond", response_model=FeedbackResponse)
async def admin_respond_to_feedback(
    feedback_id: UUID,
    response_data: AdminResponseCreate,
    admin_user: UserModel = Depends(get_current_admin_user_model),
    db: Session = Depends(get_db)
):
    """Admin endpoint to respond to feedback."""
    try:
        feedback = db.query(FeedbackModel).filter(
            FeedbackModel.id == feedback_id
        ).first()
        
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        # Update feedback with admin response
        feedback.admin_response = response_data.admin_response
        feedback.status = response_data.status
        feedback.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(feedback)
        
        return FeedbackResponse.from_orm_with_extras(feedback)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to respond to feedback: {str(e)}"
        )


@router.get("/admin/all", response_model=List[FeedbackResponse])
async def admin_get_all_feedback(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    admin_user: UserModel = Depends(get_current_admin_user_model),
    db: Session = Depends(get_db)
):
    """Admin endpoint to get all feedback with optional status filter."""
    try:
        query = db.query(FeedbackModel)
        
        if status_filter:
            query = query.filter(FeedbackModel.status == status_filter)
        
        feedback_list = query.order_by(FeedbackModel.created_at.desc()).offset(skip).limit(limit).all()
        
        return [FeedbackResponse.from_orm_with_extras(feedback) for feedback in feedback_list]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load feedback: {str(e)}"
        )


@router.get("/my/responses", response_model=List[FeedbackResponse])
async def get_my_feedback_with_responses(
    current_user: UserModel = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get user's feedback that has admin responses (for notifications/updates)."""
    try:
        feedback = db.query(FeedbackModel).filter(
            FeedbackModel.user_id == current_user.id,
            FeedbackModel.admin_response.isnot(None)  # Only feedback with responses
        ).order_by(FeedbackModel.updated_at.desc()).all()
        
        return [FeedbackResponse.from_orm_with_extras(f) for f in feedback]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load feedback responses: {str(e)}"
        ) 