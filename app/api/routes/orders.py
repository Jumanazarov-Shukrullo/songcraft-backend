"""Order routes with individual use case imports"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ...application.use_cases.create_order import CreateOrderUseCase
from ...application.use_cases.process_payment_webhook import ProcessPaymentWebhookUseCase
from ...application.dtos.order_dtos import OrderCreateDTO, OrderResponseDTO
from ...api.dependencies import get_current_user, get_unit_of_work, get_payment_service
from ...domain.entities.user import User
from ...domain.value_objects.entity_ids import OrderId


router = APIRouter(tags=["orders"])


@router.post("/", response_model=OrderResponseDTO)
async def create_order(
    order_data: OrderCreateDTO,
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work),
    payment_service = Depends(get_payment_service)
):
    """Create a new order"""
    use_case = CreateOrderUseCase(unit_of_work, payment_service)
    return await use_case.execute(order_data, current_user.id)


@router.post("/webhook")
async def payment_webhook(
    webhook_data: dict,
    unit_of_work = Depends(get_unit_of_work),
    payment_service = Depends(get_payment_service)
):
    """Process payment webhook"""
    use_case = ProcessPaymentWebhookUseCase(unit_of_work, payment_service)
    return await use_case.execute(webhook_data)


@router.get("/{order_id}", response_model=OrderResponseDTO)
async def get_order(
    order_id: str,  # Changed from int to str for UUID
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work)
):
    """Get order by ID"""
    try:
        order_repo = unit_of_work.orders
        order = await order_repo.get_by_id(OrderId.from_str(order_id))  # Use from_str for UUID string
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check if user owns this order
        if order.user_id.value != current_user.id.value:
            raise HTTPException(status_code=403, detail="Not authorized to access this order")
        
        return OrderResponseDTO.from_entity(order)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid order ID format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/", response_model=List[OrderResponseDTO])
async def get_user_orders(
    current_user: User = Depends(get_current_user),
    unit_of_work = Depends(get_unit_of_work)
):
    """Get all orders for current user"""
    order_repo = unit_of_work.orders
    orders = await order_repo.get_by_user_id(current_user.id)
    
    return [OrderResponseDTO.from_entity(order) for order in orders]


@router.get("/health")
async def orders_health():
    """Orders health check"""
    return {"status": "ok", "service": "orders"}
