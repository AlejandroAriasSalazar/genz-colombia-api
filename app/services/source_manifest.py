from pathlib import Path

import yaml

from app.models import DataSource


def read_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {
        "id",
        "name",
        "owner",
        "official_url",
        "landing_page",
        "license_name",
        "connector",
        "refresh_frequency",
        "reference_period",
        "expected_schema",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Source manifest missing fields: {sorted(missing)}")
    return data


def source_from_manifest(data: dict) -> DataSource:
    return DataSource(
        id=data["id"],
        name=data["name"],
        owner=data["owner"],
        official_url=data["official_url"],
        landing_page=data["landing_page"],
        license_name=data["license_name"],
        connector=data["connector"],
        refresh_frequency=data["refresh_frequency"],
        reference_period=data["reference_period"],
        expected_schema=data["expected_schema"],
    )
