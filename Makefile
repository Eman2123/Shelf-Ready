.PHONY: dev test lint migrate seed-demo bench-run bench-record verify-receipt verify-benchmark
dev:
	cd backend && uvicorn app.main:app --reload
test:
	cd backend && pytest
lint:
	cd backend && ruff check .
migrate:
	cd backend && alembic upgrade head
seed-demo:
	cd backend && python -m app.scripts.seed_demo
bench-run:
	cd backend && python -m app.scripts.run_benchmark
bench-record:
	cd backend && python -m app.scripts.record_run $(TASK)
verify-benchmark:
	cd backend && python -m app.scripts.verify_benchmark
verify-receipt:
	cd backend && python -m app.scripts.verify_receipt $(ID)
