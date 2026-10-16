from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    severity: int = Field(ge=1, le=5)

class Incident(IncidentCreate):
    id: int
    status: str
    created_at: datetime
    risk_score: float
    risk_level: str

class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(min_length=1, max_length=40)
    capabilities: str = ""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    available: bool = True

class AllocationCreate(BaseModel):
    incident_id: int
    resource_id: int
    start_at: datetime
    end_at: datetime

class RecommendationDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject|override)$")
    resource_id: Optional[int] = None
    reason: str = Field(default="", max_length=500)

class WhatIf(BaseModel):
    severity: Optional[int] = Field(default=None, ge=1, le=5)
    description: Optional[str] = Field(default=None, max_length=2000)

class SimulationControl(BaseModel):
    enabled: bool
