"""
Production AI Agent - Part 6 Final Project.
"""
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, record_cost
from app.redis_client import redis_healthy
from app.config import settings
from utils.mock_llm import ask as llm_ask


# --- Structured JSON logging ---
class _JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "lvl": record.levelname,
            "event": record.getMessage(),
        })


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())
logging.root.handlers = [_handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)


# --- Lifespan (graceful shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup")
    yield
    logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


# --- Health / Readiness ---
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not redis_healthy():
        from fastapi import Response
        return Response(
            content=json.dumps({"status": "not ready", "redis": False}),
            status_code=503,
            media_type="application/json",
        )
    return {"status": "ok", "redis": True}


# --- Ask ---
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="anonymous")


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    check_budget()

    t0 = time.time()
    answer = llm_ask(body.question)
    ms = round((time.time() - t0) * 1000, 1)

    # ~10 input tokens, ~20 output tokens (mock estimate)
    record_cost(10, 20)

    logger.info(json.dumps({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "lvl": "INFO",
        "event": "request",
        "path": "/ask",
        "status": 200,
        "ms": ms,
    }))

    return {"question": body.question, "answer": answer}
