from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.router import api_router
from .core.config import settings
from .core.errors import UnhandledExceptionMiddleware

app = FastAPI(
    title="ENY Consulting Platform API",
    description="Unified platform for ENY Consulting with RBAC and AI agent integration",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Starlette builds the middleware stack in reverse registration order, so the
# middleware registered first ends up innermost. This MUST be registered before
# CORSMiddleware: ServerErrorMiddleware sits outside the CORS layer, and a raw
# unhandled exception would otherwise be turned into a 500 without an
# Access-Control-Allow-Origin header. Browsers discard such responses, which is why
# the frontend reported a network error instead of the real failure.
app.add_middleware(UnhandledExceptionMiddleware)

# Set up CORS middleware. Origins are the union of BACKEND_CORS_ORIGINS and the
# documented ALLOWED_ORIGINS alias.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": "Welcome to ENY Consulting Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
