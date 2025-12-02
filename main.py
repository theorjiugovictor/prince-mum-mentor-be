from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.utils.responses import validation_error_response
from api.v1.routes import app as api_v1_router
from api.middleware.correlation_middleware import CorrelationIdMiddleware
from collections import defaultdict
from api.utils.limiter import RateLimiter

import logging

from api.utils.exception_handlers import (request_validation_exception_handler, http_exception_handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="Mum Mentor AI (NORA) API",
    description="Backend API for Mum Mentor AI - A digital companion for mothers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/api/redoc"
)
app.add_middleware(RateLimiter, limit="200/minute")

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = defaultdict(list)

    for err in exc.errors():
        # Create a path from the location tuple, skipping the first part (e.g., 'body')
        field = ".".join(map(str, err["loc"][1:]))
        message = err["msg"]
        formatted_errors[field].append(message)

    return validation_error_response(dict(formatted_errors))

app.include_router(api_v1_router, prefix="/api/v1")


# Mount static files for serving uploaded images
app.mount("/static", StaticFiles(directory="uploads"), name="static")



# Register handlers
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)


@app.get("/", tags=["Home"])
async def read_root():
    return {
        "message": "Welcome to Mum Mentor AI (NORA) API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", tags=["Home"])
async def health_check():
    return {"status": "healthy"}
