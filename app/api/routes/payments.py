"""Payment routes for handling checkout and payments"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional

from ...application.use_cases.create_order import CreateOrderUseCase
from ...application.use_cases.process_payment_webhook import ProcessPaymentWebhookUseCase
from ...application.dtos.order_dtos import OrderCreateDTO
from ...api.dependencies import get_current_user, get_unit_of_work, get_payment_service
from ...domain.entities.user import User
from ...domain.enums import ProductType


router = APIRouter(tags=["payments"])


class CreateCheckoutRequest(BaseModel):
    """Request for creating checkout"""
    product_type: str  # "audio_only" or "audio_video"
    song_data: dict


class CheckoutResponse(BaseModel):
    """Response with checkout URL"""
    checkout_url: str
    order_id: int


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    payment_service = Depends(get_payment_service)
):
    """Create checkout session for payment"""
    try:
        # Validate product type
        if request.product_type not in ["audio_only", "audio_video"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product type"
            )
        
        # Convert to domain enum
        product_type = ProductType.AUDIO_ONLY if request.product_type == "audio_only" else ProductType.AUDIO_VIDEO
        
        # Create order
        order_data = OrderCreateDTO(
            product_type=product_type,
            amount=1900 if request.product_type == "audio_only" else 2900,  # $19 or $29
            currency="USD"
        )
        
        create_order_use_case = CreateOrderUseCase(unit_of_work, payment_service)
        order = await create_order_use_case.execute(order_data, current_user.id)
        
        # Create checkout URL
        checkout_url = await payment_service.create_checkout(
            product_type=request.product_type,
            user_email=str(current_user.email),
            user_id=current_user.id.value
        )
        
        return CheckoutResponse(
            checkout_url=checkout_url,
            order_id=order.id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout: {str(e)}"
        )


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    unit_of_work = Depends(get_unit_of_work),
    payment_service = Depends(get_payment_service)
):
    """Handle payment webhook from Lemon Squeezy"""
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get("X-Signature", "")
        
        # Process webhook
        use_case = ProcessPaymentWebhookUseCase(unit_of_work, payment_service)
        success = await use_case.execute(body, signature)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/health")
async def payments_health():
    """Payments health check"""
    return {"status": "ok", "service": "payments"} 