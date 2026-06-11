"""Unit tests for the PDF ingestion pipeline (no network calls required)."""

import pytest
from app.core.ingestion import extract_text_from_pdf, split_into_chunks

SAMPLE_PDF = "tests/fixtures/sample.pdf"


def test_extract_text_from_pdf():
    with open(SAMPLE_PDF, "rb") as f:
        pdf_bytes = f.read()

    pages, total_pages = extract_text_from_pdf(pdf_bytes)
    assert total_pages >= 1
    assert isinstance(pages, list)
    assert all(isinstance(p, tuple) and len(p) == 2 for p in pages)
    # At least one page should contain text
    all_text = " ".join(text for _, text in pages)
    assert len(all_text.strip()) > 0


def test_split_into_chunks():
    with open(SAMPLE_PDF, "rb") as f:
        pdf_bytes = f.read()

    pages, _ = extract_text_from_pdf(pdf_bytes)
    chunks = split_into_chunks(pages, doc_id="test-doc-001")

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.doc_id == "test-doc-001"
        assert len(chunk.text) > 0
        assert chunk.chunk_index >= 0
        assert chunk.page_num >= 1


def test_chunks_have_correct_indices():
    with open(SAMPLE_PDF, "rb") as f:
        pdf_bytes = f.read()

    pages, _ = extract_text_from_pdf(pdf_bytes)
    chunks = split_into_chunks(pages, doc_id="test-doc-002")

    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks))), "Chunk indices should be sequential starting from 0"


def test_empty_page_produces_no_chunks():
    pages = [(1, "   \n  \t  ")]
    chunks = split_into_chunks(pages, doc_id="test-empty")
    assert len(chunks) == 0
