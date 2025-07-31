"""
FastAPI main application with DDD architecture
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.api.router import api_router
from app.db.database import SessionLocal
from app.api.routes.webhooks import webhook_dodo_proxy, webhook_gumroad_proxy

# Import all ORM models to ensure relationships are resolved
import app.infrastructure.orm  # This imports all models from __init__.py


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup - migrations handle database schema
    print("Starting Lyrzy API with DDD architecture...")
    yield
    # Shutdown
    print("Shutting down Lyrzy API...")


# Create FastAPI app
app = FastAPI(
    title="Lyrzy API",
    description="AI-powered personalized song generation platform with DDD architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Add webhook routes at root level (bypassing /api/v1 prefix)
app.api_route("/webhook_dodo", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])(webhook_dodo_proxy)
app.api_route("/webhook_gumroad", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])(webhook_gumroad_proxy)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Lyrzy API with DDD Architecture", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint that verifies database connectivity"""
    try:
        # Test database connectivity
        db = SessionLocal()
        try:
            # Execute a simple query to test connection
            result = db.execute("SELECT 1").fetchone()
            db_status = "healthy" if result else "unhealthy"
        except SQLAlchemyError as e:
            print(f"Database health check failed: {str(e)}")
            db_status = "unhealthy"
            # Still return 200 OK to avoid immediate failure, but mark as unhealthy
        finally:
            db.close()
        
        # Check Redis connectivity (optional, don't fail if Redis is down)
        redis_status = "not_configured"  # Default status
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            redis_status = "healthy"
        except Exception as e:
            print(f"Redis health check failed: {str(e)}")
            redis_status = "unhealthy"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "architecture": "DDD",
            "database": db_status,
            "redis": redis_status,
            "version": "1.0.0"
        }
        
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        # Return 200 but mark as unhealthy to help with debugging
        return {
            "status": "unhealthy",
            "error": str(e),
            "architecture": "DDD"
        }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 