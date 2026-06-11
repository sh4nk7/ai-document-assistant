.PHONY: up down build restart logs shell test lint fmt clean

up:
	docker compose -f docker/docker-compose.yml up -d

down:
	docker compose -f docker/docker-compose.yml down

build:
	docker compose -f docker/docker-compose.yml build

restart:
	docker compose -f docker/docker-compose.yml restart app

logs:
	docker compose -f docker/docker-compose.yml logs -f app

shell:
	docker compose -f docker/docker-compose.yml exec app bash

test:
	docker compose -f docker/docker-compose.yml exec app pytest tests/ -v

lint:
	ruff check app/ tests/

fmt:
	ruff format app/ tests/

clean:
	docker compose -f docker/docker-compose.yml down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# Generate LaTeX PDF (requires pdflatex)
docs:
	cd docs && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
	cp docs/main.pdf docs/ai_doc_assistant_report.pdf
	rm -f docs/main.pdf docs/main.aux docs/main.log docs/main.out docs/main.toc
