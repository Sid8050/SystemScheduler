"""
Dashboard Backend - FastAPI Application

Central management server for Endpoint Security Agent.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .models.database import init_db, engine, Base
from .api.endpoints import router as api_router
from .api.auth import router as auth_router
from .api.schedules import router as schedules_router, Schedule, ScheduleRun


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    # Create schedule tables (defined in schedules.py)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Endpoint Security Dashboard",
    description="Central management for Endpoint Security Agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(schedules_router, prefix="/api/v1/schedules", tags=["schedules"])

# Middleware to handle redirects from blocked sites
@app.middleware("http")
async def block_redirect_middleware(request: Request, call_next):
    # If the Host header doesn't match our known dashboard addresses,
    # it's likely a blocked domain being redirected here via hosts file.
    host = request.headers.get("host", "").split(":")[0]
    is_local = host in ["localhost", "127.0.0.1", "0.0.0.0"]
    
    # Simple heuristic: if it's not a local address and not an expected dashboard IP,
    # it's a blocked site. For local testing, we'll allow localhost/127.0.0.1.
    # In production, you'd check against your actual server IP.
    if not is_local and not request.url.path.startswith("/api"):
        # For browser requests to non-dashboard hosts, we want to show the blocked page.
        # However, FastAPI middleware is tricky with React routing. 
        # We'll just let it pass and let the frontend handle the Host check or provide a specific /blocked endpoint.
        pass
        
    response = await call_next(request)
    return response

@app.get("/blocked")
async def get_blocked_info():
    """Endpoint specifically for blocked site information."""
    return {"status": "blocked", "message": "Access Denied by Policy"}



@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Endpoint Security Dashboard",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


def main():
    """Run the server."""
    uvicorn.run(
        "dashboard.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
