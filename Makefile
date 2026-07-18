.PHONY: test run preflight

test:
	.venv/bin/pytest -q

run:
	.venv/bin/uvicorn app.main:app --reload --port $${PORT:-8080}

preflight:
	@.venv/bin/python -c 'from app.config import settings; print("NVIDIA key configured:", settings.has_nvidia_key); print("Kafka configured:", settings.has_kafka); print("Supabase configured:", settings.has_supabase); print("Mode:", settings.data_mode)'

