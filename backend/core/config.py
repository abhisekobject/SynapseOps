"""
SynapseOps Backend Configuration.

All configuration is sourced from environment variables.
Never hardcode secrets, credentials, or environment-specific values here.
"""

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables.

    See .env.example for the full list of supported variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = Field(default="SynapseOps", description="Application name")
    environment: str = Field(default="development", description="Runtime environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # --- API Server ---
    api_host: str = Field(default="0.0.0.0", description="API bind host")
    api_port: int = Field(default=8000, description="API bind port")

    # --- PostgreSQL ---
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="synapseops", description="PostgreSQL database name")
    postgres_user: str = Field(default="synapseops", description="PostgreSQL user")
    postgres_password: str = Field(default="", description="PostgreSQL password")

    # --- Redis ---
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database index")
    redis_password: str | None = Field(default=None, description="Redis password (optional)")

    # --- Simulation (Phase 2) ---
    sim_gateway_url: str = Field(
        default="http://sim-gateway:8100",
        description="URL of the simulated gateway service",
    )
    sim_api_url: str = Field(
        default="http://sim-api:8101",
        description="URL of the simulated API service",
    )
    sim_worker_url: str = Field(
        default="http://sim-worker:8102",
        description="URL of the simulated worker service",
    )
    sim_failure_redis_key: str = Field(
        default="sim:failures",
        description="Redis key where active failure state is published",
    )
    sim_health_poll_interval_seconds: int = Field(
        default=5,
        description="Interval (seconds) between simulated service health polls",
    )

    # --- Observability (Phase 3) ---
    otel_enabled: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing",
    )
    otel_service_name: str = Field(
        default="synapseops-api",
        description="OTel service name (used as trace service identifier)",
    )
    otel_service_version: str = Field(
        default="0.1.0",
        description="OTel service version",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP gRPC exporter endpoint (e.g. http://jaeger:4317)",
    )
    otel_exporter_otlp_insecure: bool = Field(
        default=True,
        description="Use insecure (plaintext) gRPC for OTLP export",
    )
    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics endpoint at /metrics",
    )

    # --- Intelligence (Phase 4) ---
    latency_warning_threshold_ms: float = Field(
        default=300.0,
        description="Threshold (ms) for WARNING latency events",
    )
    latency_critical_threshold_ms: float = Field(
        default=800.0,
        description="Threshold (ms) for CRITICAL latency events",
    )
    error_rate_warning_threshold: float = Field(
        default=1.0,
        description="Threshold (%) for WARNING error rate events",
    )
    error_rate_critical_threshold: float = Field(
        default=5.0,
        description="Threshold (%) for CRITICAL error rate events",
    )
    queue_warning_threshold: int = Field(
        default=10,
        description="Threshold for WARNING queue depth events",
    )
    queue_critical_threshold: int = Field(
        default=30,
        description="Threshold for CRITICAL queue depth events",
    )
    state_staleness_seconds: int = Field(
        default=15,
        description="Time (seconds) without telemetry before a service is UNKNOWN",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async PostgreSQL DSN for SQLAlchemy asyncpg driver."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """Synchronous PostgreSQL DSN for Alembic migrations."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings.

    Uses lru_cache so that settings are loaded once per process.
    In tests, clear this cache when overriding settings.
    """
    return Settings()
