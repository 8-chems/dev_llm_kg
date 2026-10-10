# Jev + LLM + Neo4j GraphRAG (Production GCP Build)

A production-grade question-answering service operating over a Neo4j knowledge graph using **Jev** for bounded decision-making, an **LLM** for text parsing/narration, and strict python code policies for thresholds and safety.

## Architecture Pipeline
`Parse (LLM) → Resolve (code+Jev) → Navigate (Jev+Neo4j) → Gate (code) → Escalate (LLM/human) → Narrate (LLM)`

## Quickstart

### Prerequisites
- Python 3.12+
- `uv` or standard Python `venv`
- Neo4j Instance (or local Docker container)

### Setup & Installation
```bash
pip install -e .[dev]
cp .env.example .env
```

### Running Locally
```bash
uvicorn src.app.main:app --reload --port 8080
```

### Running Evaluation & Calibration
```bash
python -m eval.run_eval --system S1 --split dev --out eval/runs/s1_dev.jsonl
python -m eval.calibrate --input eval/runs/s1_dev.jsonl --target-acc 0.98 --out eval/thresholds/thresholds.json
```

### Running Tests
```bash
pytest tests/unit
pytest tests/integration
```
