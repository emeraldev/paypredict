import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_project_version() -> str:
    """Read `version` from the api/ pyproject.toml so the FastAPI app and
    every OpenAPI surface track a single source of truth. Falls back to
    "0.0.0" if the file is missing (e.g. running outside an editable
    install) — the version then advertises itself as a dev build rather
    than crashing import."""
    try:
        path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        with path.open("rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (FileNotFoundError, KeyError):
        return "0.0.0"


APP_VERSION = _read_project_version()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # JWT (dashboard session auth)
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Database
    database_url: str = (
        "postgresql+asyncpg://paypredict:localdev@localhost:5434/paypredict_dev"
    )
    database_url_test: str = (
        "postgresql+asyncpg://paypredict:localdev@localhost:5434/paypredict_test"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Public-facing API URL. Declared in the OpenAPI `servers` block so
    # lender SDK code-generators know the base URL. Leave empty to omit.
    public_api_url: str = ""

    # Internal Swagger docs (`/docs/internal`) are gated by BOTH this flag
    # AND `environment != "production"` — defense in depth against an
    # accidental ENVIRONMENT misconfiguration leaking the full schema.
    # Defaults True in dev, False otherwise so staging/CI behave like prod.
    internal_docs_enabled: bool = True

    @property
    def internal_docs_visible(self) -> bool:
        """Return True only when both gates allow the internal Swagger UI."""
        return self.environment != "production" and self.internal_docs_enabled

    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def database_url_test_sync(self) -> str:
        """Synchronous test database URL for Alembic migrations in tests."""
        return self.database_url_test.replace("+asyncpg", "+psycopg2")


settings = Settings()
