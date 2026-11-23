"""
FastAPI Application Entry Point for AI Prospect Discovery API.
Endpoint: POST /prospect-discovery
Port: 4000
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import ProspectDiscoveryRequest, ProspectDiscoveryResponse
from app.services.prospect_service import prospect_service

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("prospect_discovery")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI-Powered Multi-Platform Prospect Discovery API...")
    logger.info(f"Target Port: {settings.PORT}, Host: {settings.HOST}")
    logger.info(f"LLM Provider: {settings.DEFAULT_LLM_PROVIDER}, Model: {settings.GEMINI_MODEL}")
    yield
    logger.info("Shutting down Prospect Discovery API.")


app = FastAPI(
    title="AI-Powered Multi-Platform Prospect Discovery API",
    description=(
        "Production-ready FastAPI service that receives natural language prospect search queries, "
        "extracts structured intent using LLM (Google Gemini), discovers verified public prospect profiles "
        "across Google, LinkedIn, X, YouTube, Instagram, Facebook, Threads, WhatsApp, and Email, "
        "deduplicates profiles using RapidFuzz, scores relevance, and returns consolidated prospect records."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for cross-origin integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
async def root():
    """Service status and documentation link."""
    return {
        "service": "AI-Powered Multi-Platform Prospect Discovery API",
        "status": "online",
        "documentation": "/docs",
        "endpoint": "/prospect-discovery"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "prospect-discovery-api",
        "port": settings.PORT,
        "llm_provider": settings.DEFAULT_LLM_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL
    }


@app.post(
    "/prospect-discovery",
    response_model=ProspectDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prospect Discovery"],
    summary="Discover prospects across multiple online platforms based on natural language query"
)
async def discover_prospects_endpoint(payload: ProspectDiscoveryRequest):
    """
    Accepts a natural-language query such as:
    ```json
    {
      "query": "Football lovers in Washington DC in USA"
    }
    ```
    Returns consolidated prospect records with verified public profiles and contact methods.
    """
    try:
        if not payload.query or not payload.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query parameter cannot be empty."
            )

        response = await prospect_service.discover_prospects(payload)
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error handling prospect discovery: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "query": payload.query,
                "total_prospects": 0,
                "prospects": [],
                "error": str(exc)
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
