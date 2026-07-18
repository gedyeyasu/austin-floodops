from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    data_mode: str = os.getenv("DATA_MODE", "live").lower()
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8080"))
    db_path: Path = ROOT / os.getenv("DB_PATH", "data/floodops.sqlite3")
    nws_user_agent: str = os.getenv("NWS_USER_AGENT", "AustinFloodOps/0.1 contact@example.com")
    usgs_site_id: str = os.getenv("USGS_SITE_ID", "08158000")
    usgs_parameter_codes: str = os.getenv("USGS_PARAMETER_CODES", "00060,00065")
    poll_seconds: int = int(os.getenv("POLL_SECONDS", "30"))
    heartbeat_enabled: bool = os.getenv("HEARTBEAT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    # Accept the documented names plus the initial generic names in the
    # user-provided .env file. The values are never logged or sent to the UI.
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", os.getenv("api_key", ""))
    nvidia_inference_api_key: str = os.getenv("NVIDIA_INFERENCE_API_KEY", os.getenv("NVIDI_INFERENCE_API_KEY", ""))
    nvidia_base_url: str = os.getenv("NVIDIA_BASE_URL", os.getenv("base_url", "https://integrate.api.nvidia.com/v1"))
    nemotron_model: str = os.getenv("NEMOTRON_MODEL", os.getenv("model", "nvidia/nemotron-3-nano-30b-a3b"))
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "floodops.events")
    kafka_security_protocol: str = os.getenv("KAFKA_SECURITY_PROTOCOL", "SASL_SSL")
    kafka_sasl_mechanism: str = os.getenv("KAFKA_SASL_MECHANISM", "PLAIN")
    kafka_username: str = os.getenv("KAFKA_USERNAME", "")
    kafka_password: str = os.getenv("KAFKA_PASSWORD", "")
    supabase_url: str = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_secrete_key", ""))
    hiddenlayer_interactions_url: str = os.getenv("HIDDENLAYER_INTERACTIONS_URL", "")
    hiddenlayer_api_key: str = os.getenv("HIDDENLAYER_API_KEY", "")
    hiddenlayer_project: str = os.getenv("HIDDENLAYER_PROJECT", "austin-floodops")
    # New v2 SDK - AITX 2026 key vendor
    hiddenlayer_client_id: str = os.getenv("HIDDENLAYER_CLIENT_ID", "")
    hiddenlayer_client_secret: str = os.getenv("HIDDENLAYER_CLIENT_SECRET", "")
    hiddenlayer_hl_project_id: str = os.getenv("HIDDENLAYER_HL_PROJECT_ID", "default-project")
    first_responder_webhook_url: str = os.getenv("FIRST_RESPONDER_WEBHOOK_URL", "")
    first_responder_webhook_token: str = os.getenv("FIRST_RESPONDER_WEBHOOK_TOKEN", "")
    webeoc_api_url: str = os.getenv("WEBEOC_API_URL", "https://webeoc.tdem.texas.gov/tdem/api.asmx")
    webeoc_username: str = os.getenv("WEBEOC_USERNAME", "")
    webeoc_password: str = os.getenv("WEBEOC_PASSWORD", "")
    webeoc_position: str = os.getenv("WEBEOC_POSITION", "")
    webeoc_incident: str = os.getenv("WEBEOC_INCIDENT", "")
    webeoc_board_name: str = os.getenv("WEBEOC_BOARD_NAME", "")
    webeoc_input_view_name: str = os.getenv("WEBEOC_INPUT_VIEW_NAME", "")
    openshell_gateway: str = os.getenv("OPENSHELL_GATEWAY", "")

    # --- Enterprise extensions (v0.3.0) ---
    vllm_base_url: str = os.getenv("VLLM_BASE_URL", os.getenv("VLLM_URL", "")).rstrip("/")
    vllm_model: str = os.getenv("VLLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
    vllm_api_key: str = os.getenv("VLLM_API_KEY", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-change-me-austin-floodops-jwt-secret")
    enable_rbac: bool = os.getenv("ENABLE_RBAC", "false").lower() in {"1", "true", "yes", "on"}
    osrm_base_url: str = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
    enable_prediction: bool = os.getenv("ENABLE_PREDICTION", "true").lower() in {"1", "true", "yes", "on"}
    enable_audit_chain: bool = os.getenv("ENABLE_AUDIT_CHAIN", "true").lower() in {"1", "true", "yes", "on"}

    @property
    def has_nvidia_key(self) -> bool:
        return bool(self.nvidia_api_key or self.nvidia_inference_api_key)

    @property
    def nvidia_key(self) -> str:
        return self.nvidia_inference_api_key or self.nvidia_api_key

    @property
    def has_kafka(self) -> bool:
        return bool(self.kafka_bootstrap_servers)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def has_hiddenlayer(self) -> bool:
        return bool(
            (self.hiddenlayer_interactions_url and self.hiddenlayer_api_key)
            or (self.hiddenlayer_client_id and self.hiddenlayer_client_secret)
        )

    @property
    def has_hiddenlayer_v2(self) -> bool:
        return bool(self.hiddenlayer_client_id and self.hiddenlayer_client_secret)

    @property
    def has_first_responder(self) -> bool:
        return bool(self.first_responder_webhook_url and self.first_responder_webhook_token)

    @property
    def has_webeoc(self) -> bool:
        return all(
            (
                self.webeoc_api_url,
                self.webeoc_username,
                self.webeoc_password,
                self.webeoc_position,
                self.webeoc_incident,
                self.webeoc_board_name,
                self.webeoc_input_view_name,
            )
        )

    @property
    def has_openshell(self) -> bool:
        return bool(self.openshell_gateway)

    @property
    def has_vllm(self) -> bool:
        return bool(self.vllm_base_url)

    @property
    def has_osrm(self) -> bool:
        return bool(self.osrm_base_url)


settings = Settings()
