import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import init_db
from app.api import documents, chat, search
from app.core.retrieval import ensure_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await init_db()
    await ensure_collection()
    yield


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="RAG-powered document assistant using LangChain, LangGraph, Qdrant and PostgreSQL.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(search.router, prefix="/search", tags=["Search"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
