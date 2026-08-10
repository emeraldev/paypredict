"""Regression tests for the H10 fix.

The `Settings` class refuses to boot outside the dev/test allowlist
without a real `JWT_SECRET_KEY` and `SECRET_KEY`. The check is
environment-allowlist-based (fail-closed on the environment) rather
than a literal-match on one known-bad secret value, so `""`, `"abc"`,
`"change-me-in-production-2"`, and the built-in default all fail
consistently in production/staging/anything-non-dev.
"""
import pytest
from pydantic import ValidationError

from app.config import Settings


def _build(**kwargs) -> Settings:
    """Instantiate Settings while ignoring the local `.env` file.

    Without `_env_file=None` these unit tests would inherit whatever
    `SECRET_KEY`/`JWT_SECRET_KEY` the developer's local `api/.env` sets
    — which turns a "did the validator reject this?" assertion into a
    coin flip that depends on their env. `_env_file=None` isolates the
    Settings under test to the kwargs we pass in.
    """
    return Settings(_env_file=None, **kwargs)


def test_dev_boots_with_default_secret():
    s = _build(environment="development")
    assert s.environment == "development"


def test_test_environment_boots_with_default_secret():
    s = _build(environment="test")
    assert s.environment == "test"


def test_production_refuses_default_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _build(environment="production")


def test_production_refuses_short_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _build(
            environment="production",
            jwt_secret_key="abc",
            secret_key="a" * 32,
        )


def test_production_refuses_missing_secret_key():
    """`secret_key` has no code path today but the guard still fires so
    a future consumer can't silently rely on a None."""
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _build(
            environment="production",
            jwt_secret_key="a" * 32,
            # secret_key omitted → None → rejected
        )


def test_production_boots_with_real_secrets():
    s = Settings(
        environment="production",
        jwt_secret_key="a" * 32,
        secret_key="b" * 32,
    )
    assert s.environment == "production"


def test_staging_environment_requires_secrets_too():
    """The rule is allowlist on {development, test} — every other
    environment name (staging, previews, whatever operators forget to
    classify) falls into the strict branch."""
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _build(environment="staging")


def test_production_refuses_variant_of_default_string():
    """The guard is length + allowlist, not literal match — so
    variants like `change-me-in-production-2` still fail because
    they're too short OR they equal the built-in default. Cover a
    few surface adversarial values."""
    for bad in ("", "abc", "dev-only-change-me"):
        with pytest.raises(ValidationError):
            _build(
                environment="production",
                jwt_secret_key=bad,
                secret_key="a" * 32,
            )
