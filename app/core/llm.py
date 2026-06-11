from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from app.config import settings


def get_llm() -> BaseChatModel:
    if settings.LLM_PROVIDER == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, temperature=0)
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=0,
            streaming=True,
        )


def get_embeddings() -> Embeddings:
    if settings.LLM_PROVIDER == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        return OllamaEmbeddings(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_EMBEDDING_MODEL)
    else:
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_EMBEDDING_MODEL)
