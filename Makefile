.PHONY: test run preflight smoke demo

test:
	.venv/bin/pytest -q

run:
	.venv/bin/uvicorn app.main:app --reload --port $${PORT:-8080}

smoke:
	bash scripts/smoke.sh

demo:
	bash scripts/demo.sh

preflight:
	@.venv/bin/python -c 'from app.config import settings; print("NVIDIA key configured:", settings.has_nvidia_key); print("Kafka configured:", settings.has_kafka); print("Supabase configured:", settings.has_supabase); print("HiddenLayer configured:", settings.has_hiddenlayer); print("WebEOC configured:", settings.has_webeoc); print("OpenShell gateway configured:", settings.has_openshell); print("Mode:", settings.data_mode)'
