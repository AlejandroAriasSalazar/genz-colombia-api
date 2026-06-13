"""
Schemas Pydantic para consultas de población y agregaciones.
"""
from pydantic import BaseModel, Field
from typing import Optional


class PopulationSampleRequest(BaseModel):
    """Schema de request para muestreo de población."""
    ciudad_divipola: Optional[str] = Field(None, description="Código DIVIPOLA de la ciudad")
    neighborhood_code: Optional[str] = Field(None, description="Código de barrio/comuna/localidad")
    estrato: Optional[int] = Field(None, ge=1, le=6, description="Estrato socioeconómico (1-6)")
    edad_min: Optional[int] = Field(None, ge=12, le=28, description="Edad mínima")
    edad_max: Optional[int] = Field(None, ge=12, le=28, description="Edad máxima")
    sexo: Optional[str] = Field(None, pattern="^[MF]$", description="Sexo (M o F)")
    nivel_educativo: Optional[str] = Field(None, description="Nivel educativo")
    ocupacion: Optional[str] = Field(None, description="Ocupación")
    acceso_internet: Optional[bool] = Field(None, description="Tiene acceso a internet")
    interes_musical: Optional[str] = Field(None, description="Interés musical")
    interes_tecnologico: Optional[str] = Field(None, description="Interés tecnológico")
    uso_bicicleta: Optional[str] = Field(None, description="Frecuencia de uso de bicicleta")
    sample_size: Optional[int] = Field(100, ge=1, le=1000, description="Tamaño de muestra")


class PopulationSampleResponse(BaseModel):
    """Schema de respuesta para muestreo de población."""
    count: int
    total_matching: int
    filters_applied: dict
    persons: list[dict]


class AggregateQueryRequest(BaseModel):
    """Schema de request para consultas de agregación."""
    group_by: list[str] = Field(..., description="Campos para agrupar (ej: ['ciudad_divipola', 'estrato'])")
    metric: str = Field(..., description="Métrica a calcular: count, avg_edad, pct_internet")
    ciudad_divipola: Optional[str] = Field(None, description="Filtro por ciudad")
    neighborhood_code: Optional[str] = Field(None, description="Filtro por barrio")
    estrato: Optional[int] = Field(None, ge=1, le=6, description="Filtro por estrato")
    edad_min: Optional[int] = Field(None, ge=12, le=28, description="Filtro edad mínima")
    edad_max: Optional[int] = Field(None, ge=12, le=28, description="Filtro edad máxima")
    sexo: Optional[str] = Field(None, pattern="^[MF]$", description="Filtro por sexo")


class AggregateResult(BaseModel):
    """Schema de resultado de agregación."""
    group: dict
    value: float | int


class AggregateQueryResponse(BaseModel):
    """Schema de respuesta para consultas de agregación."""
    metric: str
    group_by: list[str]
    filters_applied: dict
    results: list[AggregateResult]
    total_records: int
