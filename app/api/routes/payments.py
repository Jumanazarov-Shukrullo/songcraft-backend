"""Payment routes for handling checkout and payments"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import json

from ...application.use_cases.create_order import CreateOrderUseCase
from ...application.use_cases.create_song_from_order import CreateSongFromOrderUseCase
from ...application.dtos.order_dtos import OrderCreateDTO
from ...application.dtos.song_dtos import CreateSongRequest
from ...api.dependencies import get_current_user, get_unit_of_work, get_payment_service, get_ai_service
from ...domain.entities.user import User
from ...domain.enums import ProductType
from ...core.config import settings


router = APIRouter(tags=["payments"])


class CreateCheckoutRequest(BaseModel):
    """Request model for creating checkout session"""
    product_type: str
    amount: Optional[float] = 0
    # Song data for free orders
    song_data: Optional[dict] = None


class CheckoutResponse(BaseModel):
    """Response model for checkout session"""
    checkout_url: str
    order_id: UUID
    is_free: Optional[bool] = False
    song_id: Optional[int] = None  # For free orders


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    payment_service = Depends(get_payment_service),
    ai_service = Depends(get_ai_service)
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
            print(f"🆓 Free pricing detected for {request.product_type}, creating paid order and starting song generation")
            
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
                    # Generate unique payment ID for free orders instead of using static value
                    unique_payment_id = f"FREE_{str(uuid.uuid4())[:8]}"
                    order_entity.mark_as_paid(unique_payment_id)
                    await order_repo.update(order_entity)
                    await unit_of_work.commit()
                    print(f"✅ Order {order.id} marked as paid (FREE) with payment ID: {unique_payment_id}")
            
            # If song data is provided, create song immediately
            song_id = None
            if request.song_data:
                try:
                    print(f"🎵 Creating song immediately for free order {order.id}")
                    print(f"🎯 Song data received: {request.song_data}")
                    
                    # Validate and clean tone value
                    tone_value = request.song_data.get("tone")
                    valid_tones = ["emotional", "romantic", "playful", "ironic"]
                    if tone_value and tone_value not in valid_tones:
                        print(f"⚠️ Invalid tone '{tone_value}', setting to None")
                        tone_value = None
                    
                    # Convert song data to CreateSongRequest with validation
                    song_request = CreateSongRequest(
                        title=request.song_data.get("title", "Untitled Song"),
                        story=request.song_data.get("story") or request.song_data.get("description", ""),
                        style=request.song_data.get("style", "pop"),
                        lyrics=request.song_data.get("lyrics", ""),
                        recipient_description=request.song_data.get("recipient_description", ""),
                        occasion_description=request.song_data.get("occasion_description", ""),
                        additional_details=request.song_data.get("additional_details", ""),
                        tone=tone_value
                    )
                    
                    print(f"✅ Song request validated successfully")
                    
                    # Create song from the paid order
                    create_song_use_case = CreateSongFromOrderUseCase(unit_of_work, ai_service)
                    user_int_id = current_user.id.value if hasattr(current_user.id, "value") else int(current_user.id)
                    
                    song_response = await create_song_use_case.execute(
                        song_request, 
                        user_int_id, 
                        str(order.id)  # Pass as UUID string, not integer
                    )
                    
                    song_id = song_response.id
                    print(f"✅ Song {song_id} created and generation started for free order {order.id}")
                    
                except Exception as e:
                    print(f"❌ Error creating song for free order {order.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue without song creation - user can create it manually
                    print(f"🔄 Free order {order.id} created successfully, but song creation failed - user can create manually")
            
            # Return frontend URL for free order success
            return CheckoutResponse(
                checkout_url=f"{settings.FRONTEND_URL}/payment/success?free=true&order_id={order.id}&song_id={song_id if song_id else ''}",
                order_id=order.id,
                is_free=True,
                song_id=song_id
            )
        
        # Handle paid orders using Dodo Payments
        else:
            print(f"💳 Paid order detected for {request.product_type}, creating Dodo Payments checkout")
            
            # Create order first
            order_data = OrderCreateDTO(
                product_type=product_type,
                amount=amount,
                currency="USD"
            )
            
            create_order_use_case = CreateOrderUseCase(unit_of_work, payment_service)
            order = await create_order_use_case.execute(order_data, current_user.id)
            
            # Create Dodo Payments checkout session
            checkout_result = await payment_service.create_checkout_session(
                customer_email=str(current_user.email),
                product_type=request.product_type,
                custom_data={
                    "user_id": str(current_user.id.value if hasattr(current_user.id, "value") else current_user.id),
                    "order_id": str(order.id),
                    "customer_name": str(current_user.email).split("@")[0],
                    "song_data": json.dumps(request.song_data) if request.song_data else None
                }
            )
            
            return CheckoutResponse(
                checkout_url=checkout_result["checkout_url"],
                order_id=order.id,
                is_free=False
            )
            
    except Exception as e:
        print(f"❌ Error creating checkout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout: {str(e)}"
        )


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    unit_of_work = Depends(get_unit_of_work),
    payment_service = Depends(get_payment_service),
    ai_service = Depends(get_ai_service)
):
    """Handle payment webhooks from Dodo Payments"""
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get("webhook-signature", "")
        
        # Process webhook
        from ...application.use_cases.process_payment_webhook import ProcessPaymentWebhookUseCase
        use_case = ProcessPaymentWebhookUseCase(unit_of_work, payment_service)
        
        result = await use_case.execute(body, signature)
        
        if result:
            # For paid orders, also trigger song creation if song_data was provided
            try:
                webhook_data = json.loads(body.decode())
                payment_data = webhook_data.get("data", {})
                custom_data = payment_data.get("custom_data", {})
                
                if custom_data.get("song_data"):
                    print(f"🎵 Creating song for paid order after webhook")
                    
                    song_data = json.loads(custom_data["song_data"])
                    order_id = custom_data.get("order_id")
                    user_id = custom_data.get("user_id")
                    
                    print(f"🎯 Webhook song data: {song_data}")
                    
                    if order_id and user_id and song_data:
                        # Validate and clean tone value
                        tone_value = song_data.get("tone")
                        valid_tones = ["emotional", "romantic", "playful", "ironic"]
                        if tone_value and tone_value not in valid_tones:
                            print(f"⚠️ Invalid tone '{tone_value}', setting to None")
                            tone_value = None
                        
                        # Create song from the paid order
                        song_request = CreateSongRequest(
                            title=song_data.get("title", "Untitled Song"),
                            story=song_data.get("story") or song_data.get("description", ""),
                            style=song_data.get("style", "pop"),
                            lyrics=song_data.get("lyrics", ""),
                            recipient_description=song_data.get("recipient_description", ""),
                            occasion_description=song_data.get("occasion_description", ""),
                            additional_details=song_data.get("additional_details", ""),
                            tone=tone_value
                        )
                        
                        print(f"✅ Webhook song request validated successfully")
                        
                        create_song_use_case = CreateSongFromOrderUseCase(unit_of_work, ai_service)
                        song_response = await create_song_use_case.execute(song_request, int(user_id), order_id)  # Pass order_id as string, not int
                        
                        print(f"✅ Song {song_response.id} created for paid order {order_id}")
                        
            except Exception as e:
                print(f"❌ Error creating song for paid order: {e}")
                # Continue - webhook processed successfully even if song creation failed
            
            return {"status": "success"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook"
            )
            
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.get("/health")
async def payments_health():
    """Payments health check"""
    return {"status": "ok", "service": "payments"} 