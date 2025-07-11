"""Payment routes for handling checkout and payments"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from ...application.use_cases.create_order import CreateOrderUseCase
from ...application.use_cases.process_payment_webhook import ProcessPaymentWebhookUseCase
from ...application.dtos.order_dtos import OrderCreateDTO
from ...api.dependencies import get_current_user, get_unit_of_work, get_payment_service
from ...domain.entities.user import User
from ...domain.enums import ProductType
from ...core.config import settings


router = APIRouter(tags=["payments"])


class CreateCheckoutRequest(BaseModel):
    """Request for creating checkout"""
    product_type: str  # "audio_only" or "audio_video"


class CheckoutResponse(BaseModel):
    """Response with checkout URL"""
    checkout_url: str
    order_id: UUID
    is_free: Optional[bool] = False


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    payment_service = Depends(get_payment_service)
):
    """Create checkout session for payment or handle free orders"""
    try:
        # Validate product type
        if request.product_type not in ["audio_only", "audio_video"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product type"
            )
        
        # Convert to domain enum
        product_type = ProductType.AUDIO_ONLY if request.product_type == "audio_only" else ProductType.AUDIO_VIDEO
        
        # Get pricing for product type
        amount = settings.AUDIO_PRICE if request.product_type == "audio_only" else settings.VIDEO_PRICE
        
        # Check if pricing is free (0 cents)
        if amount == 0:
            print(f"🆓 Free pricing detected for {request.product_type}, creating paid order directly")
            
            # Create order with free pricing
            order_data = OrderCreateDTO(
                product_type=product_type,
                amount=amount,
                currency="USD"
            )
            
            create_order_use_case = CreateOrderUseCase(unit_of_work, payment_service)
            order = await create_order_use_case.execute(order_data, current_user.id)
            
            # Mark order as paid immediately for free products
            async with unit_of_work:
                order_repo = unit_of_work.orders
                from ...domain.value_objects.entity_ids import OrderId
                order_entity = await order_repo.get_by_id(OrderId.from_str(str(order.id)))
                if order_entity:
                    order_entity.mark_as_paid("FREE_PRODUCT")  # Use special payment ID for free
                    await order_repo.update(order_entity)
                    await unit_of_work.commit()
                    print(f"✅ Order {order.id} marked as paid (FREE)")
            
            # Return frontend URL for processing free order
            return CheckoutResponse(
                checkout_url=f"{settings.FRONTEND_URL}/payment/success?free=true&order_id={order.id}",
                order_id=order.id,
                is_free=True
            )
        
        # Standard paid flow - create order and redirect to Dodo Payments
        order_data = OrderCreateDTO(
            product_type=product_type,
            amount=amount,
            currency="USD"
        )
        
        create_order_use_case = CreateOrderUseCase(unit_of_work, payment_service)
        order = await create_order_use_case.execute(order_data, current_user.id)
        
        # Create checkout URL with order_id in custom_data
        checkout_result = await payment_service.create_checkout_session(
            customer_email=str(current_user.email),
            product_type=request.product_type,
            custom_data={
                "user_id": str(current_user.id.value),
                "order_id": str(order.id),
                "customer_name": str(current_user.email).split("@")[0]  # Extract name from email
            }
        )
        
        return CheckoutResponse(
            checkout_url=checkout_result["checkout_url"],
            order_id=order.id,
            is_free=False
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
    """Handle payment webhook from Dodo Payments"""
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