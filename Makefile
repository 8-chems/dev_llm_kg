.PHONY: install test test-unit test-int lint format run calibrate eval

install:
	pip install -e .[dev]

test:
	pytest tests/

test-unit:
	pytest tests/unit

test-int:
	pytest tests/integration

lint:
	ruff check src/ tests/ eval/
	mypy src/

format:
	ruff format src/ tests/ eval/

run:
	uvicorn src.app.main:app --host 0.0.0.0 --port 8080 --reload

eval:
	python -m eval.run_eval --system S1 --split dev --out eval/runs/s1_dev.jsonl

calibrate:
	python -m eval.calibrate --input eval/runs/s1_dev.jsonl --target-acc 0.98 --out eval/thresholds/thresholds.json
