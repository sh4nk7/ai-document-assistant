# AI Document Assistant

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)
![LangChain](https://img.shields.io/badge/LangChain-0.3-orange)

> **RAG-powered document assistant** — carica PDF, fai domande in linguaggio naturale, cerca semanticamente tra i tuoi documenti.

---

## Panoramica

AI Document Assistant è un'applicazione web full-stack che permette di:

- **Caricare PDF** e indicizzarli automaticamente in un database vettoriale
- **Chattare** con i tuoi documenti tramite un chatbot RAG (Retrieval-Augmented Generation)
- **Cercare semanticamente** per significato, non per parola chiave esatta
- **Streammare** le risposte token per token (Server-Sent Events)

### Architettura Tecnica

```
Client HTTP
    │
    ▼
┌─────────────────────────────────────────┐
│          FastAPI Application            │
│   /documents   /chat   /search          │
└───────────┬────────────────┬────────────┘
            │                │
            ▼                ▼
┌───────────────────┐  ┌────────────────┐
│  LangGraph RAG    │  │  PostgreSQL 16 │
│  ┌─────────────┐  │  │  documents     │
│  │embed_query  │  │  │  conversations │
│  │search_qdrant│  │  └────────────────┘
│  │build_prompt │  │
│  │call_llm     │  │
│  └─────────────┘  │
└─────────┬─────────┘
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
┌────────┐  ┌──────────────────┐
│ Qdrant │  │ OpenAI / Ollama  │
│doc_    │  │ LLM + Embeddings │
│chunks  │  └──────────────────┘
└────────┘
```

---

## Stack Tecnologico

| Componente | Tecnologia |
|-----------|-----------|
| Backend API | FastAPI 0.115 + Uvicorn |
| Orchestrazione LLM | LangChain 0.3 + **LangGraph 0.2** |
| LLM | OpenAI GPT-4o-mini / Ollama Llama 3.2 |
| Embedding | text-embedding-3-small (1536-dim) |
| Vector DB | **Qdrant** (similarità coseno) |
| Database | **PostgreSQL 16** + SQLAlchemy 2.0 async |
| Parsing PDF | pypdf 5 |
| Deploy | Docker Compose |

---

## Avvio Rapido

### Prerequisiti

- Docker ≥ 24 e Docker Compose ≥ 2.20
- Chiave API OpenAI (oppure Ollama installato)

### 1. Configurazione

```bash
cp docker/.env.example docker/.env
# Modifica docker/.env e inserisci OPENAI_API_KEY=sk-...
```

### 2. Build e avvio

```bash
docker compose -f docker/docker-compose.yml up --build -d

# oppure con Make:
make build && make up
```

### 3. Verifica

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0"}
```

La **Swagger UI** è disponibile su → [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Esempi d'Uso

### Carica un PDF

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/percorso/al/documento.pdf"
```

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "documento_abc123.pdf",
  "upload_date": "2026-06-11T10:30:00+00:00",
  "total_chunks": 47,
  "total_pages": 8,
  "status": "ready"
}
```

### Fai una domanda (RAG)

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quali sono i punti principali del capitolo 3?",
    "doc_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "top_k": 4
  }'
```

```json
{
  "session_id": "abc-123",
  "answer": "Il capitolo 3 tratta di...",
  "sources": [
    {"text": "...chunk rilevante...", "page_num": 12, "score": 0.89}
  ]
}
```

### Streaming (SSE)

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"question": "Riassumi il documento", "stream": true}'
# data: Il
# data:  documento
# data:  descrive...
# data: [DONE]
```

### Ricerca semantica

```bash
curl "http://localhost:8000/search/?q=reti+neurali&top_k=5"
```

---

## Variabili d'Ambiente

| Variabile | Default | Descrizione |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | `openai` o `ollama` |
| `OPENAI_API_KEY` | — | Chiave API OpenAI |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modello chat |
| `QDRANT_VECTOR_SIZE` | `1536` | Dim. vettori (768 per Ollama) |
| `CHUNK_SIZE` | `500` | Dimensione chunk |
| `CHUNK_OVERLAP` | `50` | Overlap chunk |
| `TOP_K` | `4` | Chunk per query RAG |

Vedere `docker/.env.example` per la lista completa.

---

## Uso con Ollama (locale, privato)

```bash
# In docker/.env:
LLM_PROVIDER=ollama
QDRANT_VECTOR_SIZE=768

# Decommentare il servizio ollama in docker/docker-compose.yml, poi:
docker compose -f docker/docker-compose.yml up --build -d
docker exec ai_doc_ollama ollama pull llama3.2
docker exec ai_doc_ollama ollama pull nomic-embed-text
```

---

## Test

```bash
# Esegui i test all'interno del container
make test

# Oppure in locale (con ambiente Python attivo e servizi running)
pytest tests/ -v
```

Il file `tests/fixtures/sample.pdf` è incluso per i test automatici.

---

## Struttura del Progetto

```
ai-document-assistant/
├── app/
│   ├── main.py              # Entry point FastAPI
│   ├── config.py            # Impostazioni (pydantic-settings)
│   ├── api/                 # Endpoint: documents, chat, search
│   ├── core/                # Pipeline: ingestion, retrieval, llm
│   ├── models/              # Modelli SQLAlchemy
│   ├── db/                  # Session async, CRUD
│   └── utils/               # Validazione file
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── docs/                    # Documentazione LaTeX
│   └── main.tex
├── tests/
│   ├── fixtures/sample.pdf  # PDF di test
│   ├── test_api.py
│   └── test_ingestion.py
├── requirements.txt
└── Makefile
```

---

## Documentazione

La documentazione tecnica completa in formato PDF è disponibile in [`docs/`](docs/).

Compilare da sorgente LaTeX:
```bash
make docs
# oppure: cd docs && pdflatex main.tex && pdflatex main.tex
```

---

## Licenza

MIT License — vedi [LICENSE](LICENSE) per i dettagli.
