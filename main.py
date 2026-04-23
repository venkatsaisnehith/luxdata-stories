"""LuxData Stories — main application entry point."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import router
from core.scheduler import start_scheduler, run_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    print("LuxData Stories: Starting up...")
    start_scheduler()
    # Run initial pipeline in background
    asyncio.create_task(run_pipeline())
    yield
    # Shutdown
    print("LuxData Stories: Shutting down...")


app = FastAPI(
    title="LuxData Stories",
    description="Public data from Luxembourg, explained simply",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(router)

# Mount static files for frontend assets (CSS, JS)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main dashboard page."""
    return FileResponse("frontend/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
