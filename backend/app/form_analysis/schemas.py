"""
Form Analysis Pydantic Schemas
Defines structured telemetry for rule-based form evaluation, severity levels, measurements, and limitations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class FormFindingMeasurement(BaseModel):
    name: str
    value: Optional[float] = None
    unit: str = "degrees"


class FormFinding(BaseModel):
    code: str
    severity: str = Field("info", description="Severity level: 'info', 'warning', or 'unavailable'")
    message: str
    recommendation: str
    measurement: Optional[FormFindingMeasurement] = None


class FormAnalysisResult(BaseModel):
    exercise: Optional[str] = None
    analysis_available: bool = True
    form_status: str = Field("good", description="'good', 'needs_attention', or 'unavailable'")
    findings: List[FormFinding] = []
    limitations: List[str] = []
