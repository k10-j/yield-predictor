"""
schemas.py - Pydantic models for the Crop Yield Predictor API (Area/Item version)
"""

from pydantic import BaseModel, Field, field_validator

from prediction import ALLOWED_AREAS, ALLOWED_ITEMS, FEATURE_RANGES


class CropFeatures(BaseModel):
    area: str = Field(..., description="Country name", json_schema_extra={"example": "Rwanda"})
    item: str = Field(..., description="Crop name", json_schema_extra={"example": "Maize"})
    year: int = Field(
        ..., ge=FEATURE_RANGES["year"][0], le=FEATURE_RANGES["year"][1],
        json_schema_extra={"example": 2013},
    )
    average_rain_fall_mm_per_year: float = Field(
        ..., ge=FEATURE_RANGES["average_rain_fall_mm_per_year"][0],
        le=FEATURE_RANGES["average_rain_fall_mm_per_year"][1],
        json_schema_extra={"example": 1200.0},
    )
    pesticides_tonnes: float = Field(
        ..., ge=FEATURE_RANGES["pesticides_tonnes"][0],
        le=FEATURE_RANGES["pesticides_tonnes"][1],
        json_schema_extra={"example": 50.0},
    )
    avg_temp: float = Field(
        ..., ge=FEATURE_RANGES["avg_temp"][0], le=FEATURE_RANGES["avg_temp"][1],
        json_schema_extra={"example": 19.5},
    )

    @field_validator("area")
    @classmethod
    def area_must_be_known(cls, v):
        if v not in ALLOWED_AREAS:
            raise ValueError(f"'{v}' is not a supported country. See GET /metadata for the full list.")
        return v

    @field_validator("item")
    @classmethod
    def item_must_be_known(cls, v):
        if v not in ALLOWED_ITEMS:
            raise ValueError(f"'{v}' is not a supported crop. Must be one of: {ALLOWED_ITEMS}")
        return v


class PredictionResponse(BaseModel):
    predicted_yield_tonnes_per_ha: float
    model_used: str


class MetadataResponse(BaseModel):
    areas: list[str]
    items: list[str]
    ranges: dict
    model_used: str
    test_mse: float
    target_units: str


class RetrainRecord(CropFeatures):
    yield_tonnes_per_ha: float = Field(..., ge=0, le=100, description="True observed yield")


class RetrainRequest(BaseModel):
    records: list[RetrainRecord]


class RetrainResponse(BaseModel):
    message: str
    n_new_records: int
    n_total_records: int
    test_mse_before: float
    test_mse_after: float
