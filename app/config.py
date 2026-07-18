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
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_inference_api_key: str = os.getenv("NVIDIA_INFERENCE_API_KEY", "")
    nvidia_base_url: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    nemotron_model: str = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3-nano-30b-a3b")
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "floodops.events")
    kafka_security_protocol: str = os.getenv("KAFKA_SECURITY_PROTOCOL", "SASL_SSL")
    kafka_sasl_mechanism: str = os.getenv("KAFKA_SASL_MECHANISM", "PLAIN")
    kafka_username: str = os.getenv("KAFKA_USERNAME", "")
    kafka_password: str = os.getenv("KAFKA_PASSWORD", "")
    supabase_url: str = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    hiddenlayer_interactions_url: str = os.getenv("HIDDENLAYER_INTERACTIONS_URL", "")
    hiddenlayer_api_key: str = os.getenv("HIDDENLAYER_API_KEY", "")
    hiddenlayer_project: str = os.getenv("HIDDENLAYER_PROJECT", "austin-floodops")
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
        return bool(self.hiddenlayer_interactions_url and self.hiddenlayer_api_key)

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


settings = Settings()
