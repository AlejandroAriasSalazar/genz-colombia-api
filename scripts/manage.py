import argparse
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.plans import plan_limits, plan_scopes
from app.core.security import digest_api_key, generate_api_key
from app.database import SessionLocal
from app.models import ApiClient
from app.services.releases import create_candidate_release, publish_release, sync_source_manifest

DEFAULT_MANIFEST = Path("config/sources/dane_population_projections.yaml")


def register_source(args) -> None:
    with SessionLocal.begin() as db:
        source = sync_source_manifest(db, Path(args.manifest))
        print(f"registered source: {source.id}")


def ingest(args) -> None:
    settings = get_settings()
    years = set(range(args.year_start, args.year_end + 1))
    with SessionLocal.begin() as db:
        release = create_candidate_release(
            db,
            settings,
            Path(args.manifest),
            Path(args.local_source) if args.local_source else None,
            years,
        )
        print(
            f"candidate={release.version} status={release.status.value} "
            f"cells={release.row_count} quality={release.quality_report['status']}"
        )


def publish(args) -> None:
    with SessionLocal.begin() as db:
        release = publish_release(db, args.version)
        print(f"published={release.version}")


def create_key(args) -> None:
    settings = get_settings()
    per_minute, per_day, max_sample = plan_limits(args.tier)
    plain_key, prefix = generate_api_key()
    with SessionLocal.begin() as db:
        if db.scalar(select(ApiClient).where(ApiClient.key_prefix == prefix)):
            raise RuntimeError("Generated duplicate prefix; retry")
        db.add(
            ApiClient(
                name=args.name,
                key_prefix=prefix,
                key_digest=digest_api_key(plain_key, settings.api_key_pepper),
                tier=args.tier,
                scopes=plan_scopes(args.tier),
                requests_per_minute=per_minute,
                requests_per_day=per_day,
                max_sample_size=max_sample,
            )
        )
    print("API key created. It will not be shown again:")
    print(plain_key)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GenZ Colombia API V3 operations")
    sub = parser.add_subparsers(required=True)

    source_parser = sub.add_parser("register-source")
    source_parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    source_parser.set_defaults(func=register_source)

    ingest_parser = sub.add_parser("ingest")
    ingest_parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ingest_parser.add_argument("--local-source")
    ingest_parser.add_argument("--year-start", type=int, default=2018)
    ingest_parser.add_argument("--year-end", type=int, default=2042)
    ingest_parser.set_defaults(func=ingest)

    publish_parser = sub.add_parser("publish")
    publish_parser.add_argument("version")
    publish_parser.set_defaults(func=publish)

    key_parser = sub.add_parser("create-key")
    key_parser.add_argument("--name", required=True)
    key_parser.add_argument("--tier", choices=["free", "pro", "enterprise"], default="free")
    key_parser.set_defaults(func=create_key)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
