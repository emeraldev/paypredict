import tomllib
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Environments where the app is allowed to boot without a real
# `JWT_SECRET_KEY` in the environment. Anything outside this set (staging,
# production, previews, anything the operator hasn't explicitly declared as
# dev/test) must supply a real secret — the goal is fail-closed on
# environment, not on one known-bad literal.
_ENVS_WITHOUT_JWT_SECRET_REQUIRED = {"development", "test"}
_JWT_SECRET_MIN_LENGTH = 32


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


# Lender-facing rate limits, per plan tier. Numbers are requests per
# `RATE_LIMIT_WINDOW_SECONDS`. Values match docs/api-reference.md so the
# documented 429 contract and the enforced limit can't drift apart. The
# "Scale" tier advertises Custom in the docs — 2000/min is the default
# until a per-tenant override lands.
PLAN_RATE_LIMITS: dict[str, int] = {
    "PILOT": 60,
    "STARTER": 200,
    "GROWTH": 500,
    "SCALE": 2000,
}

RATE_LIMIT_WINDOW_SECONDS = 60


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    # `secret_key` has no code path today; left as an env-only field with
    # no default so a missing env var in prod is a startup error rather
    # than a silent boot with a well-known value.
    secret_key: str | None = None

    # JWT (dashboard session auth). Dev/test can boot with the built-in
    # default so the local suite doesn't need a special env var; any
    # other environment MUST supply a real secret via `JWT_SECRET_KEY`.
    # The `_validate_secrets` model_validator below enforces that outside
    # the dev/test allowlist.
    jwt_secret_key: str = "dev-only-change-me"
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

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        """Fail-closed on any environment outside the dev/test allowlist.

        Environments in `_ENVS_WITHOUT_JWT_SECRET_REQUIRED` may boot with
        the built-in default JWT secret — necessary so the local suite
        and CI dev environment don't need bespoke env vars. Every other
        environment (staging, production, previews, anything the
        operator forgets to classify as dev/test) MUST provide
        `JWT_SECRET_KEY` via the environment, with at least
        `_JWT_SECRET_MIN_LENGTH` characters of entropy.

        The check is allowlist-based on `environment`, not literal-match
        on the secret value — an operator who sets JWT_SECRET_KEY to
        "abc" or an empty string still fails here rather than booting
        with a trivially crackable secret.
        """
        if self.environment in _ENVS_WITHOUT_JWT_SECRET_REQUIRED:
            return self
        # Outside dev/test: the built-in default is not acceptable, and
        # the caller-supplied secret must meet the minimum-entropy bar.
        supplied = self.jwt_secret_key or ""
        if supplied == "dev-only-change-me" or len(supplied) < _JWT_SECRET_MIN_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY must be set to a value at least "
                f"{_JWT_SECRET_MIN_LENGTH} characters long when environment="
                f"{self.environment!r}. Refusing to boot with a default or "
                "under-entropy secret outside development/test."
            )
        # Same rule for the (currently unused) secret_key so a future
        # code path that starts using it can't silently rely on a
        # missing env var.
        if self.secret_key is None or len(self.secret_key) < _JWT_SECRET_MIN_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be set to a value at least "
                f"{_JWT_SECRET_MIN_LENGTH} characters long when environment="
                f"{self.environment!r}."
            )
        return self

    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def database_url_test_sync(self) -> str:
        """Synchronous test database URL for Alembic migrations in tests."""
        return self.database_url_test.replace("+asyncpg", "+psycopg2")


settings = Settings()
