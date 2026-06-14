import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class ReleaseStatus(str, enum.Enum):
    candidate = "candidate"
    published = "published"
    rejected = "rejected"
    superseded = "superseded"


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    landing_page: Mapped[str] = mapped_column(Text, nullable=False)
    license_name: Mapped[str] = mapped_column(String(120), nullable=False)
    connector: Mapped[str] = mapped_column(String(40), nullable=False)
    refresh_frequency: Mapped[str] = mapped_column(String(60), nullable=False)
    reference_period: Mapped[str] = mapped_column(String(80), nullable=False)
    expected_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    snapshots: Mapped[list["SourceSnapshot"]] = relationship(back_populates="source")


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), nullable=False, index=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    http_etag: Mapped[str | None] = mapped_column(String(300))
    http_last_modified: Mapped[str | None] = mapped_column(String(200))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[DataSource] = relationship(back_populates="snapshots")
    versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="snapshot")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("source_snapshots.id"), nullable=False)
    status: Mapped[ReleaseStatus] = mapped_column(
        Enum(ReleaseStatus, native_enum=False), nullable=False, default=ReleaseStatus.candidate
    )
    method_version: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_start: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_end: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_report: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    snapshot: Mapped[SourceSnapshot] = relationship(back_populates="versions")
    cells: Mapped[list["PopulationCell"]] = relationship(
        back_populates="dataset_version", cascade="all, delete-orphan"
    )


class PopulationCell(Base):
    __tablename__ = "population_cells"
    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id",
            "municipality_code",
            "year",
            "area",
            "sex",
            "age",
            name="uq_population_cell_dimension",
        ),
        CheckConstraint("population >= 0", name="ck_population_nonnegative"),
        CheckConstraint("age >= 0 AND age <= 100", name="ck_population_age"),
        Index("ix_population_release_query", "dataset_version_id", "year", "municipality_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False
    )
    department_code: Mapped[str] = mapped_column(String(2), nullable=False)
    department_name: Mapped[str] = mapped_column(String(120), nullable=False)
    municipality_code: Mapped[str] = mapped_column(String(5), nullable=False)
    municipality_name: Mapped[str] = mapped_column(String(150), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    area: Mapped[str] = mapped_column(String(40), nullable=False)
    sex: Mapped[str] = mapped_column(String(1), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    population: Mapped[int] = mapped_column(Integer, nullable=False)

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="cells")


class ApiClient(Base):
    __tablename__ = "api_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    key_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    requests_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    requests_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    max_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    api_client_id: Mapped[str | None] = mapped_column(ForeignKey("api_clients.id"))
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(200), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    client_ip_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
