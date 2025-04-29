import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routers import city, graph, package_routes

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SMHI Temperature Data API",
    description="API for accessing and visualizing temperature data from SMHI",
    version="0.1.0",
)

# Add CORS middleware with expanded configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (including frontend container)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Content-Type", "X-Content-Type-Options"],
)

# Include routers with /api prefix only
app.include_router(package_routes.router, prefix="/api")
app.include_router(city.router, prefix="/api")
app.include_router(graph.router, prefix="/api")

# Serve frontend if it exists
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        """Serve the frontend index.html file"""
        index_path = frontend_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            return {
                "message": "Welcome to SMHI Temperature API. Frontend not available."
            }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Test route to verify API access
@app.get("/api/test", include_in_schema=False)
async def test():
    """Test endpoint to verify API access"""
    logger.debug("Test endpoint was called")
    return {"status": "API working"}


if __name__ == "__main__":
    import uvicorn

    # Use uvicorn to run the app directly if this file is executed
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
