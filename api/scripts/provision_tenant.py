"""One-command tenant provisioning for live pilots.

Creates (Tenant, Admin User, FactorWeight × factors, ApiKey) on the
currently-configured database and prints the credentials. Reads the
same `DATABASE_URL` the API uses, so running this on a Fly machine
via `flyctl ssh console` targets the prod Neon branch; running
locally against docker-compose targets your dev DB.

Usage (interactive, prints a secret-free summary + the raw API key
ONCE — capture the API key output immediately, it's not recoverable):

    python -m scripts.provision_tenant \
        --name "Kalene Lending" \
        --market ZM \
        --factor-set PAYROLL \
        --plan STARTER \
        --admin-email ignatius@kalene.co.zm \
        --admin-name "Mr. Ignatius" \
        --methods PAYROLL

Add `--dry-run` to see what WOULD happen without writing. On any
real IntegrityError (duplicate email, duplicate api-key lookup_id)
the script aborts cleanly without partial state — everything runs
in one DB transaction.

Nothing in this script is Kalene-specific; it also provisions
future lender tenants with different (market, factor_set, methods)
tuples. For Lumo-style mobile money: `--factor-set MOBILE_WALLET
--methods MOBILE_MONEY`. For SA BNPL: `--market SA --factor-set
CARD_DEBIT --methods CARD,DEBIT_ORDER`.

A policy-compliant admin password is generated automatically if
`--admin-password` is omitted. Standard-out ONLY — never log to
disk.
"""
from __future__ import annotations

import argparse
import asyncio
import secrets
import string
import sys
import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select

from app.database import async_session
from app.models.api_key import ApiKey
from app.models.factor_weight import FactorWeight
from app.models.score_request import CollectionMethod
from app.models.tenant import FactorSet, Market, Plan, Tenant
from app.models.user import User, UserRole
from app.scoring.registry import get_default_weights_for_method
from app.services.api_key_service import mint_key
from app.services.auth_service import hash_password


_METHOD_CHOICES = [m.value for m in CollectionMethod]


def _generate_admin_password() -> str:
    """Policy-compliant random password: 20 chars, three character
    classes (upper + lower + digit + symbol). Printed to stdout once
    and never stored anywhere else."""
    alphabet_upper = string.ascii_uppercase
    alphabet_lower = string.ascii_lowercase
    alphabet_digit = string.digits
    alphabet_symbol = "-._~"
    # Guarantee one of each class, then fill with the full union.
    all_chars = alphabet_upper + alphabet_lower + alphabet_digit + alphabet_symbol
    required = [
        secrets.choice(alphabet_upper),
        secrets.choice(alphabet_lower),
        secrets.choice(alphabet_digit),
        secrets.choice(alphabet_symbol),
    ]
    rest = [secrets.choice(all_chars) for _ in range(16)]
    chars = required + rest
    # Shuffle the required chars into random positions.
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Provision a new lender tenant on the current DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--name", required=True, help="Tenant display name, e.g. 'Kalene Lending'.")
    p.add_argument("--market", required=True, choices=[m.value for m in Market])
    p.add_argument(
        "--factor-set",
        required=True,
        choices=[fs.value for fs in FactorSet],
        help="Tenant's default factor set (dashboard default; actual scoring is picked per collection_method).",
    )
    p.add_argument(
        "--plan",
        default=Plan.PILOT.value,
        choices=[p_.value for p_ in Plan],
        help="Rate-limit tier. Default PILOT (60 req/min).",
    )
    p.add_argument("--admin-email", required=True)
    p.add_argument("--admin-name", required=True)
    p.add_argument(
        "--admin-password",
        default=None,
        help="If omitted, a strong password is generated and printed once.",
    )
    p.add_argument(
        "--methods",
        required=True,
        help=f"Comma-separated collection methods to seed factor weights for. One of: {','.join(_METHOD_CHOICES)}.",
    )
    p.add_argument(
        "--api-key-label",
        default="Production key",
        help="Human label shown in the dashboard's API Keys tab.",
    )
    p.add_argument(
        "--env-prefix",
        default="pk_live_",
        choices=["pk_live_", "pk_test_"],
        help="API key prefix. pk_live_ for real traffic; pk_test_ for pilots that haven't gone to real volume.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs + print what would be created, but don't write.",
    )
    return p.parse_args()


async def _provision(args: argparse.Namespace) -> dict:
    """One transaction. On any failure, nothing is committed."""
    methods_raw = [m.strip() for m in args.methods.split(",") if m.strip()]
    for m in methods_raw:
        if m not in _METHOD_CHOICES:
            raise ValueError(
                f"--methods: '{m}' is not a valid CollectionMethod. "
                f"Choose from {','.join(_METHOD_CHOICES)}."
            )
    methods = [CollectionMethod(m) for m in methods_raw]

    admin_password = args.admin_password or _generate_admin_password()
    api_key_raw, api_key_lookup, api_key_display = mint_key(args.env_prefix)
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        # Pre-flight: reject a duplicate admin email cleanly, before
        # anything else is written. The DB has a UNIQUE on
        # users.email; without this check the IntegrityError would
        # abort the whole transaction but with a cryptic Postgres
        # message rather than the clear line below.
        existing = await session.scalar(
            select(User).where(User.email == args.admin_email.lower())
        )
        if existing is not None:
            raise RuntimeError(
                f"user with email '{args.admin_email}' already exists "
                f"(tenant_id={existing.tenant_id}). Pick a different email."
            )

        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name=args.name,
            market=Market(args.market),
            factor_set=FactorSet(args.factor_set),
            plan=Plan(args.plan),
            is_active=True,
            webhook_secret=f"whsec_{secrets.token_urlsafe(32)}",
        )
        session.add(tenant)

        admin = User(
            tenant_id=tenant_id,
            email=args.admin_email.lower(),
            name=args.admin_name,
            password_hash=hash_password(admin_password),
            role=UserRole.ADMIN,
            # Stamped so JWT iat-vs-password_changed_at revocation
            # has a real timestamp to compare against (otherwise NULL
            # means "every token always valid").
            password_changed_at=now,
        )
        session.add(admin)

        for method in methods:
            for factor_name, weight in get_default_weights_for_method(method).items():
                session.add(
                    FactorWeight(
                        tenant_id=tenant_id,
                        collection_method=method.value,
                        factor_name=factor_name,
                        weight=weight,
                    )
                )

        key_hash = bcrypt.hashpw(
            api_key_raw.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        session.add(
            ApiKey(
                tenant_id=tenant_id,
                lookup_id=api_key_lookup,
                key_hash=key_hash,
                key_prefix=api_key_display,
                label=args.api_key_label,
                is_active=True,
            )
        )

        if args.dry_run:
            # Pydantic / ORM instance surface is enough — just show
            # the user what WOULD land, roll back cleanly.
            await session.rollback()
            print("--- DRY RUN (no commit) ---", file=sys.stderr)
        else:
            await session.commit()

    return {
        "tenant_id": str(tenant_id),
        "tenant_name": args.name,
        "admin_email": args.admin_email,
        "admin_password": admin_password,
        "api_key_raw": api_key_raw,
        "api_key_prefix": api_key_display,
        "api_key_label": args.api_key_label,
        "methods": [m.value for m in methods],
    }


def _print_summary(result: dict) -> None:
    """Non-secret summary first (safe to log / share), credentials
    block last (capture these immediately, they are never recoverable)."""
    print()
    print(f"Tenant ID:    {result['tenant_id']}")
    print(f"Tenant name:  {result['tenant_name']}")
    print(f"Methods:      {', '.join(result['methods'])}")
    print(f"API key:      {result['api_key_prefix']}  (label: {result['api_key_label']})")
    print()
    print("=" * 72)
    print("CREDENTIALS — capture these NOW; they are not recoverable.")
    print("=" * 72)
    print()
    print(f"Dashboard login: {result['admin_email']}")
    print(f"Dashboard pw:    {result['admin_password']}")
    print()
    print(f"API key (full):  {result['api_key_raw']}")
    print()


def main() -> int:
    args = _parse_args()
    try:
        result = asyncio.run(_provision(args))
    except Exception as exc:
        print(f"\nAborting: {exc}", file=sys.stderr)
        return 1
    _print_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
