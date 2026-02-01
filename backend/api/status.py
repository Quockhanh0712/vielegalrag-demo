"""
Status API Endpoint - System Health Check.
"""
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
try:
    import torch
except ImportError:
    torch = None

from backend.config import settings
from backend.db.schemas import SystemStatus, ComponentStatus
from backend.utils.logger import get_logger

logger = get_logger("api.status")

router = APIRouter()


async def check_qdrant() -> ComponentStatus:
    """Check Qdrant connection."""
    start = time.time()
    try:
        from backend.core.qdrant_store import get_qdrant_connector
        connector = get_qdrant_connector()
        
        if connector.check_connection():
            collections = connector.list_collections()
            latency = (time.time() - start) * 1000
            
            if not collections:
                return ComponentStatus(
                    status="warning",
                    message=f"Connected to {settings.QDRANT_HOST[:20]}... but no collections found",
                    latency_ms=latency
                )
                
            return ComponentStatus(
                status="connected",
                message=f"Collections: {', '.join(collections)}",
                latency_ms=latency
            )
        else:
            return ComponentStatus(
                status="error",
                message=f"Connection failed to {settings.QDRANT_HOST} (Check QDRANT_HOST/API_KEY)"
            )
    except Exception as e:
        return ComponentStatus(
            status="error",
            message=str(e)
        )


async def check_ollama() -> ComponentStatus:
    """Check LLM Provider availability."""
    start = time.time()
    try:
        from backend.core.llm_factory import get_llm_factory
        factory = get_llm_factory()
        config = factory.get_active_config()
        
        latency = (time.time() - start) * 1000
        status = "available"
        msg = f"Provider: {config['provider_name']} | Model: {config['model']}"
        
        if not config["has_api_key"] and config["provider"] != "local_ollama":
            status = "warning"
            msg = f"{config['provider_name']}: Waiting for API Key"
            
        return ComponentStatus(
            status=status,
            message=msg,
            latency_ms=latency
        )
    except Exception as e:
        return ComponentStatus(
            status="error",
            message=str(e)
        )


async def check_embedding() -> ComponentStatus:
    """Check embedding model."""
    start = time.time()
    try:
        from backend.core.embeddings import get_embedding_model
        model = get_embedding_model()
        
        # Quick test embedding
        if model.is_loaded():
            latency = (time.time() - start) * 1000
            return ComponentStatus(
                status="loaded",
                message=f"Device: {model.device}",
                latency_ms=latency
            )
        else:
            return ComponentStatus(
                status="not_loaded",
                message="Model not yet loaded (lazy loading)"
            )
    except Exception as e:
        return ComponentStatus(
            status="error",
            message=str(e)
        )


async def check_database() -> ComponentStatus:
    """Check database connection."""
    start = time.time()
    try:
        from backend.db.database import get_session
        
        from sqlalchemy import text
        async with get_session() as session:
            # Simple query to test connection
            await session.execute(text("SELECT 1"))
        
        latency = (time.time() - start) * 1000
        return ComponentStatus(
            status="connected",
            message="SQLite OK",
            latency_ms=latency
        )
    except Exception as e:
        return ComponentStatus(
            status="error",
            message=str(e)
        )


@router.get("/status", response_model=SystemStatus)
async def get_status():
    """
    Get system status including all components.
    
    Returns health status of:
    - Qdrant vector database
    - Ollama LLM service
    - Embedding model
    - SQLite database
    - GPU availability
    """
    logger.info("Status check requested")
    
    # Run checks (some can be parallelized if needed)
    qdrant_status = await check_qdrant()
    ollama_status = await check_ollama()
    embedding_status = await check_embedding()
    database_status = await check_database()
    
    # Check GPU
    gpu_available = False
    if torch is not None:
        gpu_available = torch.cuda.is_available()
    
    return SystemStatus(
        qdrant=qdrant_status,
        ollama=ollama_status,
        embedding=embedding_status,
        database=database_status,
        gpu_available=gpu_available,
        timestamp=datetime.utcnow()
    )


@router.get("/status/quick")
async def quick_status():
    """
    Quick status check - just returns OK if server is running.
    Useful for load balancers and basic health checks.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "gpu": torch.cuda.is_available() if torch else False
    }
