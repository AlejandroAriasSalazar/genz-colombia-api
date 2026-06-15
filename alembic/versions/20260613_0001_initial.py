"""Initial production schema.

Revision ID: 20260613_0001
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "20260613_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("owner", sa.String(200), nullable=False),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("landing_page", sa.Text(), nullable=False),
        sa.Column("license_name", sa.String(120), nullable=False),
        sa.Column("connector", sa.String(40), nullable=False),
        sa.Column("refresh_frequency", sa.String(60), nullable=False),
        sa.Column("reference_period", sa.String(80), nullable=False),
        sa.Column("expected_schema", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(80), sa.ForeignKey("data_sources.id"), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("http_etag", sa.String(300)),
        sa.Column("http_last_modified", sa.String(200)),
        sa.Column(
            "retrieved_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_source_snapshots_source_id", "source_snapshots", ["source_id"])
    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.String(50), nullable=False, unique=True),
        sa.Column("snapshot_id", sa.String(36), sa.ForeignKey("source_snapshots.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "candidate",
                "published",
                "rejected",
                "superseded",
                name="releasestatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("method_version", sa.String(40), nullable=False),
        sa.Column("reference_start", sa.Integer(), nullable=False),
        sa.Column("reference_end", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("quality_report", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "population_cells",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_version_id",
            sa.String(36),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("department_code", sa.String(2), nullable=False),
        sa.Column("department_name", sa.String(120), nullable=False),
        sa.Column("municipality_code", sa.String(5), nullable=False),
        sa.Column("municipality_name", sa.String(150), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("area", sa.String(40), nullable=False),
        sa.Column("sex", sa.String(1), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("population", sa.Integer(), nullable=False),
        sa.CheckConstraint("population >= 0", name="ck_population_nonnegative"),
        sa.CheckConstraint("age >= 0 AND age <= 100", name="ck_population_age"),
        sa.UniqueConstraint(
            "dataset_version_id",
            "municipality_code",
            "year",
            "area",
            "sex",
            "age",
            name="uq_population_cell_dimension",
        ),
    )
    op.create_index(
        "ix_population_release_query",
        "population_cells",
        ["dataset_version_id", "year", "municipality_code"],
    )
    op.create_table(
        "api_clients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False, unique=True),
        sa.Column("key_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("requests_per_minute", sa.Integer(), nullable=False),
        sa.Column("requests_per_day", sa.Integer(), nullable=False),
        sa.Column("max_sample_size", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_api_clients_key_prefix", "api_clients", ["key_prefix"], unique=True)
    op.create_table(
        "query_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("api_client_id", sa.String(36), sa.ForeignKey("api_clients.id")),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(200), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("client_ip_hash", sa.String(64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_query_logs_request_id", "query_logs", ["request_id"])


def downgrade() -> None:
    op.drop_table("query_logs")
    op.drop_table("api_clients")
    op.drop_table("population_cells")
    op.drop_table("dataset_versions")
    op.drop_table("source_snapshots")
    op.drop_table("data_sources")
