"""Pydantic models for API request/response."""

from pydantic import BaseModel, Field


class OptimizationRequest(BaseModel):
    region: str = Field(..., description="DHMT region name")
    strategy: str = Field("nominal", description="nominal | static_robust | adr")
    scenario: str = Field("2526", description="CMS scenario: 2526 | 2627")
    periods: int = Field(12, ge=1, le=52, description="Number of biweekly periods")
    kappa: float = Field(10.0, gt=0, description="Negative binomial dispersion")
    gamma: float = Field(10.0, ge=0, description="Robustness budget (Gamma)")
    transport_cost_per_km: float = Field(0.5, ge=0)
    shortage_penalty: float = Field(5.0, ge=0, description="Shortage penalty as multiplier of procurement cost per drug")
    holding_cost: float = Field(0.1, ge=0)
    supply_multiplier: float = Field(0.0, ge=0)
    seed: int = Field(42)
    use_cms_data: bool = Field(True, description="Use CMS product-level data")
    demand_multiplier: float = Field(
        1.0, ge=0,
        description="Global multiplier applied to all demand values (1.0 = no change)",
    )
    custom_demand: dict[str, dict[str, float]] | None = Field(
        None,
        description=(
            "Optional custom demand matrix overriding computed values. "
            "Keys are facility names, values are dicts of {drug_class: demand_value}. "
            "Facilities not listed keep their computed demand."
        ),
    )


class OptimizationResult(BaseModel):
    region: str
    strategy: str
    periods: list[dict]
    summary: dict


class PlanningRequest(BaseModel):
    region: str = Field(..., description="DHMT region name")
    strategy: str = Field("static_robust", description="nominal | static_robust | adr")
    scenario: str = Field("2526", description="CMS scenario: 2526 | 2627")
    kappa: float = Field(10.0, gt=0)
    gamma: float = Field(10.0, ge=0)
    transport_cost_per_km: float = Field(0.5, ge=0)
    shortage_penalty: float = Field(5.0, ge=0, description="Multiplier of procurement cost")
    holding_cost: float = Field(0.1, ge=0)
    use_cms_data: bool = Field(True)
    initial_inventory: dict[str, dict[str, float]] | None = Field(
        None,
        description="Current inventory: {facility: {drug: quantity}}. Omit for zero stock.",
    )
    last_demand: dict[str, dict[str, float]] | None = Field(
        None,
        description="Last period realized demand: {facility: {drug: quantity}}. "
                    "If provided, used as mean demand instead of forecast.",
    )
    custom_prices: dict[str, float] | None = Field(
        None,
        description="Override unit prices: {drug_code: price_bwp}. "
                    "Drugs not listed keep their CMS price.",
    )


class FacilitySummary(BaseModel):
    total_facilities: int
    total_population: int
    dhmt_count: int
    facility_type_counts: dict
    dhmt_facility_counts: dict


class RegionInfo(BaseModel):
    name: str
    facility_count: int
    source_node: str
