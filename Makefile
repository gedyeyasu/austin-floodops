.PHONY: test run preflight smoke demo docker-build docker-run docker-down docker-logs

test:
	.venv/bin/pytest -q

run:
	.venv/bin/uvicorn app.main:app --reload --port $${PORT:-8080}

smoke:
	bash scripts/smoke.sh

demo:
	bash scripts/demo.sh

preflight:
	@.venv/bin/python -c 'from app.config import settings; print("NVIDIA key configured:", settings.has_nvidia_key); print("Kafka configured:", settings.has_kafka); print("Supabase configured:", settings.has_supabase); print("HiddenLayer configured:", settings.has_hiddenlayer); print("WebEOC configured:", settings.has_webeoc); print("OpenShell gateway configured:", settings.has_openshell); print("vLLM configured:", settings.has_vllm); print("OSRM configured:", settings.has_osrm); print("RBAC enabled:", settings.enable_rbac); print("Prediction enabled:", settings.enable_prediction); print("Audit chain enabled:", settings.enable_audit_chain); print("Mode:", settings.data_mode)'

docker-build:
	docker build -t austin-floodops:0.3.0 .

docker-run:
	docker-compose up --build -d
	@echo "App at http://127.0.0.1:8080  (health: /health)"
	@echo "Logs: make docker-logs"

docker-down:
	docker-compose down -v

docker-logs:
	docker-compose logs -f app

docker-probe:
	curl -s http://127.0.0.1:8080/health | python -m json.tool || curl -s http://127.0.0.1:8080/health
	curl -s -X POST http://127.0.0.1:8080/api/integrations/vllm/probe | python -m json.tool || true
	curl -s -X POST http://127.0.0.1:8080/api/integrations/osrm/probe | python -m json.tool || true
