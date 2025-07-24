"""Payment routes for handling checkout and payments"""

import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

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
    song_id: Optional[UUID] = None  # For free orders - changed from int to UUID


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
                    user_uuid_str = str(current_user.id.value)  # Get UUID string from UserId object
                    
                    song_response = await create_song_use_case.execute(
                        song_request, 
                        user_uuid_str, 
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
        
        # Handle paid orders using Stripe
        else:
            print(f"💳 Paid order detected for {request.product_type}, creating Stripe checkout")
            
            # Create order first
            order_data = OrderCreateDTO(
                product_type=product_type,
                amount=amount,
                currency="USD"
            )
            
            create_order_use_case = CreateOrderUseCase(unit_of_work, payment_service)
            order = await create_order_use_case.execute(order_data, current_user.id)
            
            # Create Stripe checkout session
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
            
            # CRITICAL FIX: Update the order with Stripe session ID
            async with unit_of_work:
                order_repo = unit_of_work.orders
                from ...domain.value_objects.entity_ids import OrderId
                order_entity = await order_repo.get_by_id(OrderId.from_str(str(order.id)))
                if order_entity:
                    # Store the Stripe session ID in the order for webhook processing
                    order_entity.stripe_session_id = checkout_result["checkout_id"]
                    await order_repo.update(order_entity)
                    await unit_of_work.commit()
                    print(f"✅ Order {order.id} linked to Stripe session: {checkout_result['checkout_id']}")
                else:
                    print(f"❌ Failed to find order {order.id} for session linking")
            
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


@router.get("/session/{session_id}")
async def get_order_from_session(
    session_id: str,
    payment_service = Depends(get_payment_service)
):
    """Get order information from Stripe session ID"""
    print(f"🔍 Getting session info for: {session_id}")
    
    try:
        # Get session details from Stripe
        import stripe
        from ...core.config import settings
        
        # Make sure Stripe is configured
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        print(f"🔧 Retrieving Stripe session: {session_id}")
        session = stripe.checkout.Session.retrieve(session_id)
        print(f"✅ Session retrieved successfully")
        
        metadata = session.metadata or {}
        order_id = metadata.get('order_id')
        user_id = metadata.get('user_id')
        product_type = metadata.get('product_type')
        
        print(f"📋 Session metadata: {metadata}")
        
        if not order_id:
            print(f"❌ No order_id found in session metadata: {metadata}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order ID not found in session metadata"
            )
        
        result = {
            "order_id": order_id,
            "user_id": user_id,
            "product_type": product_type,
            "session_id": session_id,
            "payment_status": session.payment_status
        }
        
        print(f"✅ Returning session data: {result}")
        return result
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    unit_of_work = Depends(get_unit_of_work),
    payment_service = Depends(get_payment_service),
    ai_service = Depends(get_ai_service)
):
    """Handle payment webhooks from Stripe"""
    try:
        # Get raw body and all relevant headers
        body = await request.body()
        
        # Validate basic webhook requirements
        if len(body) == 0:
            print("⚠️ Webhook rejected: Empty body")
            return {"status": "error", "detail": "Empty webhook body"}, 400
        
        # Check all possible webhook signature headers for Stripe and legacy providers
        signature_headers = {
            "stripe-signature": request.headers.get("stripe-signature", ""),
            "webhook-signature": request.headers.get("webhook-signature", ""),
            "x-webhook-signature": request.headers.get("x-webhook-signature", ""),
            "dodo-signature": request.headers.get("dodo-signature", ""),
            "signature": request.headers.get("signature", ""),
            "authorization": request.headers.get("authorization", "")
        }
        
        print(f"📨 Webhook received:")
        print(f"   Body size: {len(body)} bytes")
        print(f"   Content-Type: {request.headers.get('content-type', 'unknown')}")
        print(f"   User-Agent: {request.headers.get('user-agent', 'unknown')}")
        print(f"   All signature headers: {signature_headers}")
        
        # Try to find the signature in various headers
        signature = ""
        signature_source = ""
        for header_name, header_value in signature_headers.items():
            if header_value:
                signature = header_value
                signature_source = header_name
                break
        
        if signature:
            print(f"   Using signature from header: {signature_source}")
        else:
            print(f"   ⚠️ No signature found in any header")
        
        # Log the body content for debugging (first 500 chars)
        body_preview = body.decode('utf-8', errors='ignore')[:500]
        print(f"   Body preview: {body_preview}")
        
        # Process webhook
        from ...application.use_cases.process_payment_webhook import ProcessPaymentWebhookUseCase
        use_case = ProcessPaymentWebhookUseCase(unit_of_work, payment_service)
        
        # Pass headers to the webhook processing for better debugging
        result = await use_case.execute(body, signature, dict(request.headers))
        
        if result:
            # Webhook processed successfully - credits were already added in the use case
            print("✅ Webhook processed successfully")
            return {"status": "success"}
        else:
            # Webhook verification failed - return 400, not 500
            print("❌ Webhook verification failed")
            return {"status": "error", "detail": "Webhook verification failed"}, 400
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in webhook body: {e}")
        return {"status": "error", "detail": "Invalid JSON format"}, 400
        
    except ValueError as e:
        print(f"❌ Webhook validation error: {e}")
        return {"status": "error", "detail": str(e)}, 400
        
    except Exception as e:
        print(f"❌ Unexpected error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        # Return 422 for processing errors, not 500
        return {"status": "error", "detail": "Webhook processing failed"}, 422


@router.get("/health")
async def payments_health():
    """Payments health check"""
    return {"status": "ok", "service": "payments"}


@router.post("/webhook/test")
async def test_webhook():
    """Test webhook endpoint for debugging - returns webhook info without processing"""
    return {
        "status": "test_endpoint", 
        "message": "This is a test endpoint. Real webhooks are processed at POST /webhook",
        "emergency_bypass_active": True,
        "expected_headers": [
            "webhook-signature",
            "user-agent: DodoPayments/v1"
        ],
        "expected_body": {
            "type": "payment.succeeded",
            "business_id": "bus_...",
            "data": {
                "payment_id": "pay_...",
                "status": "succeeded"
            }
        }
    } 