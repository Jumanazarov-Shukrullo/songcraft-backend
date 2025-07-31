"""Webhook routes for redirecting to external services"""

import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

# Supabase function URLs
SUPABASE_WEBHOOK_DODO_URL = "https://jrrmltzkitwllnidcpwr.supabase.co/functions/v1/webhook-dodo"
SUPABASE_WEBHOOK_GUMROAD_URL = "https://jrrmltzkitwllnidcpwr.supabase.co/functions/v1/webhook-gumroad"


@router.api_route("/webhook_dodo", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def webhook_dodo_proxy(request: Request):
    """Proxy all requests to Supabase webhook-dodo function"""
    try:
        # DEBUG: Simple response first to test if route works
        return {"status": "debug", "message": "Webhook route is working", "method": request.method}
        
        # Get request body
        body = await request.body()
        
        # Get headers, excluding hop-by-hop headers
        headers = {
            key: value for key, value in request.headers.items()
            if key.lower() not in ["host", "content-length", "transfer-encoding", "connection", "upgrade"]
        }
        
        # Make request to Supabase function
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=SUPABASE_WEBHOOK_DODO_URL,
                headers=headers,
                params=request.query_params,
                content=body
            )
            
        # Return the response with same status code, headers and content
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except httpx.TimeoutException:
        logger.error("Timeout when proxying request to Supabase webhook-dodo")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout when connecting to webhook service"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error when proxying to Supabase webhook-dodo: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error when connecting to webhook service"
        )
    except Exception as e:
        logger.error(f"Unexpected error in webhook_dodo_proxy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.api_route("/webhook_gumroad", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def webhook_gumroad_proxy(request: Request):
    """Proxy all requests to Supabase webhook-gumroad function"""
    try:
        # DEBUG: Simple response first to test if route works
        return {"status": "debug", "message": "Gumroad webhook route is working", "method": request.method}
        
        # Get request body
        body = await request.body()
        
        # Get headers, excluding hop-by-hop headers
        headers = {
            key: value for key, value in request.headers.items()
            if key.lower() not in ["host", "content-length", "transfer-encoding", "connection", "upgrade"]
        }
        
        # Make request to Supabase function
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=SUPABASE_WEBHOOK_GUMROAD_URL,
                headers=headers,
                params=request.query_params,
                content=body
            )
            
        # Return the response with same status code, headers and content
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except httpx.TimeoutException:
        logger.error("Timeout when proxying request to Supabase webhook-gumroad")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout when connecting to webhook service"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error when proxying to Supabase webhook-gumroad: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error when connecting to webhook service"
        )
    except Exception as e:
        logger.error(f"Unexpected error in webhook_gumroad_proxy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 