from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PopulationFilters(StrictModel):
    municipality_code: str | None = Field(None, pattern=r"^\d{5}$")
    year: int | None = Field(None, ge=2018, le=2042)
    age_min: int = Field(12, ge=0, le=100)
    age_max: int = Field(28, ge=0, le=100)
    sex: Literal["M", "F"] | None = None

    @model_validator(mode="after")
    def validate_age_range(self) -> "PopulationFilters":
        if self.age_min > self.age_max:
            raise ValueError("age_min must be less than or equal to age_max")
        return self


class SampleRequest(StrictModel):
    filters: PopulationFilters = Field(default_factory=PopulationFilters)
    sample_size: int = Field(100, ge=1, le=1000)
    seed: int = Field(42, ge=0, le=2_147_483_647)
    dataset_version: str | None = None


class SyntheticPerson(BaseModel):
    synthetic_id: str
    age: int
    sex: Literal["M", "F"]
    municipality_code: str
    municipality_name: str
    reference_year: int


class SampleResponse(BaseModel):
    count: int
    seed: int
    filters_applied: dict
    dataset: dict
    persons: list[SyntheticPerson]


class AggregateRequest(StrictModel):
    group_by: list[Literal["municipality_code", "year", "age", "sex"]] = Field(min_length=1, max_length=2)
    metric: Literal["population", "share_percent"] = "population"
    filters: PopulationFilters = Field(default_factory=PopulationFilters)
    dataset_version: str | None = None

    @model_validator(mode="after")
    def unique_group_by(self) -> "AggregateRequest":
        if len(set(self.group_by)) != len(self.group_by):
            raise ValueError("group_by fields must be unique")
        return self


class AggregateItem(BaseModel):
    group: dict
    value: float | int | None
    suppressed: bool = False


class AggregateResponse(BaseModel):
    metric: str
    group_by: list[str]
    filters_applied: dict
    dataset: dict
    total_population: int
    results: list[AggregateItem]
