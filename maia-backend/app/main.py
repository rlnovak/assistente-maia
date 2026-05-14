from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.middleware.rate_limit import limiter
from app.middleware.request_id import RequestIdMiddleware

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("maia_api_start", env=settings.ENV, llm_provider=settings.LLM_PROVIDER, llm_model=settings.LLM_MODEL)
    yield
    log.info("maia_api_stop")


app = FastAPI(
    title="MaIA API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Rate limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middlewares ────────────────────────────────────────────────────────────────
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
from app.api.v1.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.webhooks.hubla import router as hubla_router
from app.api.v1.webhooks.whatsapp import router as whatsapp_router

app.include_router(health_router, prefix="/v1")
app.include_router(chat_router, prefix="/v1")
app.include_router(conversations_router, prefix="/v1")
app.include_router(hubla_router, prefix="/v1")
app.include_router(whatsapp_router, prefix="/v1")
