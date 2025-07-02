"""Main API router for DDD architecture"""

from fastapi import APIRouter

# Import all DDD routes
from .routes import auth, songs, orders, admin, files, users, payments

# Main API router
api_router = APIRouter()

# Include all routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(songs.router, prefix="/songs", tags=["songs"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(files.router, prefix="/files", tags=["files"])

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"} 